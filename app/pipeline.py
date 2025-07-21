"""
NLP Pipeline with separated model management
Models:
1. Typhoon Translate 4B (GGUF via llama-cpp)
2. XLM-RoBERTa (Transformers)
3. Typhoon 2.1 4B Instruct (Transformers)
"""

import os
import json
import re
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import XLMRobertaModel, AutoConfig, PreTrainedModel, AutoTokenizer
from safetensors.torch import load_file as safe_load_file
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from together import Together
except ImportError:
    Together = None
    print("Warning: together package not installed. GrammarExplainer will use mock explanations.")


def extract_first_sentence(text):
    """
    Extract the first sentence from English text.
    Returns tuple of (first_sentence, is_multi_sentence)
    """
    if not text:
        return text, False
    
    # Simple sentence splitting using common sentence endings
    # Handle common abbreviations that shouldn't split sentences
    text = text.strip()
    
    # Replace common abbreviations temporarily to avoid false splits
    abbreviations = {
        'Mr.': 'Mr<DOT>',
        'Mrs.': 'Mrs<DOT>',
        'Ms.': 'Ms<DOT>',
        'Dr.': 'Dr<DOT>',
        'Ph.D.': 'PhD<DOT>',
        'i.e.': 'ie<DOT>',
        'e.g.': 'eg<DOT>',
        'etc.': 'etc<DOT>',
        'vs.': 'vs<DOT>',
        'U.S.': 'US<DOT>',
        'U.K.': 'UK<DOT>'
    }
    
    temp_text = text
    for abbr, replacement in abbreviations.items():
        temp_text = temp_text.replace(abbr, replacement)
    
    # Split on sentence endings followed by space and capital letter
    # or end of string
    sentence_pattern = r'([.!?]+)\s+(?=[A-Z])|([.!?]+)$'
    matches = list(re.finditer(sentence_pattern, temp_text))
    
    if not matches:
        # No sentence ending found, treat whole text as one sentence
        return text, False
    
    # Get the end position of the first sentence
    first_end = matches[0].end()
    first_sentence = temp_text[:first_end].strip()
    
    # Restore abbreviations
    for abbr, replacement in abbreviations.items():
        first_sentence = first_sentence.replace(replacement, abbr)
    
    # Check if there's more text after the first sentence
    remaining_text = temp_text[first_end:].strip()
    is_multi_sentence = bool(remaining_text)
    
    return first_sentence, is_multi_sentence


class XLMRHierClassifier(PreTrainedModel):
    """
    Hierarchical XLM-RoBERTa classifier for tense classification
    Predicts both coarse (Past/Present/Future) and fine-grained tense labels
    """
    config_class = AutoConfig

    def __init__(self, config, n_coarse=3, n_fine=25, coarse_w=0.3):
        super().__init__(config)
        self.encoder = XLMRobertaModel(config, add_pooling_layer=False)
        h = self.encoder.config.hidden_size

        # Dual classification heads
        self.coarse_head = nn.Linear(h, n_coarse)  # Past/Present/Future
        self.fine_head = nn.Linear(h, n_fine)      # Detailed tense categories

        self.crit = nn.CrossEntropyLoss()
        self.coarse_w = coarse_w  # Loss weighting
        self.post_init()

    def forward(self, input_ids=None, attention_mask=None, labels=None, **_):
        # Encode input
        hidden = self.encoder(input_ids, attention_mask=attention_mask).last_hidden_state
        pooled = hidden[:, 0]  # Use CLS token

        # Predict both levels
        logits_c = self.coarse_head(pooled)
        logits_f = self.fine_head(pooled)

        if labels is None:
            return {"logits": (logits_c, logits_f)}

        # Calculate hierarchical loss
        lab_c, lab_f = labels[:, 0], labels[:, 1]
        loss_c = self.crit(logits_c, lab_c)

        mask = lab_f != -100
        if mask.any():
            loss_f = self.crit(logits_f[mask], lab_f[mask])
            loss = self.coarse_w * loss_c + (1 - self.coarse_w) * loss_f
        else:
            loss = loss_c

        return {"loss": loss, "logits": (logits_c, logits_f)}


class TenseTagDefinitions:
    """Comprehensive tense tag definitions for grammar explanations"""

    def __init__(self):
        # Coarse-level definitions
        self.coarse_definitions = {
            "Past": "หมายถึง เหตุการณ์หรือการกระทำที่เกิดขึ้นและจบลงแล้วในอดีต",
            "Present": "หมายถึง เหตุการณ์หรือการกระทำที่เกิดขึ้นในปัจจุบัน หรือเป็นความจริงทั่วไป",
            "Future": "หมายถึง เหตุการณ์หรือการกระทำที่จะเกิดขึ้นในอนาคต"
        }

        # Fine-grained tense definitions with detailed explanations
        self.fine_definitions = {
            # Present Simple categories
            "HABIT": {
                "tense": "Present Simple",
                "thai_name": "Present Simple - กิจวัตร/นิสัย",
                "usage": "ใช้เมื่อพูดถึงกิจวัตรหรือพฤติกรรมที่ทำเป็นประจำ",
                "structure": "Subject + V1 (ถ้าประธานเอกพจน์เติม s/es)",
                "keywords": "always, usually, often, sometimes, every day",
                "example": "I drink coffee every morning."
            },
            "FACT": {
                "tense": "Present Simple",
                "thai_name": "Present Simple - ข้อเท็จจริง",
                "usage": "ใช้กับข้อเท็จจริงที่เป็นสัจธรรมหรือเป็นความรู้ทางวิทยาศาสตร์",
                "structure": "Subject + V1",
                "keywords": "ข้อเท็จจริงทั่วไป, สัจธรรม",
                "example": "The sun rises in the east."
            },
            "SCHEDULEDFUTURE": {
                "tense": "Present Simple",
                "thai_name": "Present Simple - ตารางเวลา/แผนการที่กำหนดไว้",
                "usage": "ใช้เมื่อกล่าวถึงตารางเวลา ตารางเดินรถ แผนที่กำหนดไว้แน่นอน หรือแผนการในอนาคตที่วางไว้",
                "structure": "Subject + V1",
                "keywords": "schedule, timetable, plan to, intend to",
                "example": "The train leaves at 9 AM. / I plan to study abroad next year."
            },
            "SAYING": {
                "tense": "Present Simple",
                "thai_name": "Present Simple - สุภาษิต/คำพังเพย",
                "usage": "ใช้กับสุภาษิต คำพังเพย หรือคำกล่าวทั่วไป",
                "structure": "Subject + V1",
                "keywords": "สุภาษิต, คำกล่าว",
                "example": "Practice makes perfect."
            },
            "HEADLINE": {
                "tense": "Present Simple",
                "thai_name": "Present Simple - พาดหัวข่าว",
                "usage": "ใช้ในพาดหัวข่าวหรือข้อความที่เน้นย่อประโยค แม้จะพูดถึงเหตุการณ์ที่เกิดขึ้นแล้ว เพื่อสร้างความรู้สึกสดใหม่",
                "structure": "Subject + V1",
                "keywords": "พาดหัวข่าว",
                "example": "Prime Minister visits flood victims."
            },

            # Present Continuous categories
            "HAPPENING": {
                "tense": "Present Continuous",
                "thai_name": "Present Continuous - กำลังเกิดขึ้น",
                "usage": "สิ่งที่ทำอยู่ขณะพูด",
                "structure": "Subject + is/am/are + V-ing",
                "keywords": "now, right now, at the moment",
                "example": "I am writing an email now."
            },
            "NOWADAYS": {
                "tense": "Present Continuous",
                "thai_name": "Present Continuous - ช่วงนี้",
                "usage": "สิ่งที่ทำอยู่ในช่วงนี้ เช่น โปรเจค หรือสิ่งที่ใช้เวลาทำนานเป็นหลักวัน",
                "structure": "Subject + is/am/are + V-ing",
                "keywords": "these days, nowadays, currently",
                "example": "I am working on a big project these days."
            },
            "SUREFUT": {
                "tense": "Present Continuous",
                "thai_name": "Present Continuous - อนาคตที่วางแผนไว้",
                "usage": "เหตุการณ์ที่จะเกิดขึ้นในอนาคตโดยมีการวางแผนไว้แล้ว มักเจอ be + going to",
                "structure": "Subject + is/am/are + going to + V1",
                "keywords": "tomorrow, next week, planning",
                "example": "I am going to visit my parents tomorrow."
            },
            "PROGRESS": {
                "tense": "Present Continuous",
                "thai_name": "Present Continuous - กำลังเปลี่ยนแปลง",
                "usage": "เหตุการณ์ที่กำลังมีการเปลี่ยนแปลง พัฒนาขึ้น หรือก้าวหน้าขึ้น",
                "structure": "Subject + is/am/are + V-ing",
                "keywords": "changing, improving, getting better",
                "example": "The weather is getting warmer."
            },

            # Present Perfect categories
            "JUSTFIN": {
                "tense": "Present Perfect",
                "thai_name": "Present Perfect - เพิ่งจบ",
                "usage": "ใช้เมื่อเหตุการณ์เพิ่งจะสิ้นสุดลง",
                "structure": "Subject + have/has + V3",
                "keywords": "just, just now",
                "example": "I have just finished my homework."
            },
            "RESULT": {
                "tense": "Present Perfect",
                "thai_name": "Present Perfect - มีผลถึงปัจจุบัน",
                "usage": "สิ่งที่เกิดขึ้นตั้งแต่อดีตและมีผลหรือคงสภาพจนถึงปัจจุบัน",
                "structure": "Subject + have/has + V3",
                "keywords": "already, yet, still",
                "example": "I have lost my keys."
            },
            "EXP": {
                "tense": "Present Perfect",
                "thai_name": "Present Perfect - ประสบการณ์",
                "usage": "ประสบการณ์ (เจอคำว่า First / ... time)",
                "structure": "Subject + have/has + V3",
                "keywords": "ever, never, first time",
                "example": "This is the first time I have visited Japan."
            },

            # Present Perfect Continuous
            "SINCEFOR": {
                "tense": "Present Perfect Continuous",
                "thai_name": "Present Perfect Continuous - ทำมาตั้งแต่",
                "usage": "สิ่งที่ทำเรื่อยมาจนถึงปัจจุบัน โดยเน้นระยะเวลา มักเจอ for/since",
                "structure": "Subject + have/has + been + V-ing",
                "keywords": "for, since, all day",
                "example": "I have been studying for 3 hours."
            },

            # Past Simple
            "NORFIN": {
                "tense": "Past Simple",
                "thai_name": "Past Simple - อดีตทั่วไป",
                "usage": "การกระทำในอดีตทั่วไป โดยไม่มีบริบทหรือรายละเอียดเพิ่มเติม",
                "structure": "Subject + V2",
                "keywords": "yesterday, last week, ago",
                "example": "I went to school yesterday."
            },

            # Past Continuous
            "INTERRUPT": {
                "tense": "Past Continuous",
                "thai_name": "Past Continuous - ถูกขัดจังหวะ",
                "usage": "ใช้คู่กับ Past Simple เพื่อบอกว่าเหตุการณ์ใน Past simple เกิดแทรกอีกเหตุการณ์ที่กำลังทำในอดีต",
                "structure": "Subject + was/were + V-ing + when + Past Simple",
                "keywords": "when, while",
                "example": "I was sleeping when the phone rang."
            },
            "DOINGATSOMETIMEPAST": {
                "tense": "Past Continuous",
                "thai_name": "Past Continuous - กำลังทำในอดีต",
                "usage": "สิ่งที่กำลังทำอยู่ ณ เวลาหนึ่งในอดีต",
                "structure": "Subject + was/were + V-ing",
                "keywords": "at ... yesterday, at that time",
                "example": "I was reading at 8 PM yesterday."
            },

            # Past Perfect
            "BEFOREPAST": {
                "tense": "Past Perfect",
                "thai_name": "Past Perfect - ก่อนเหตุการณ์ในอดีต",
                "usage": "ใช้เมื่อต้องการแสดงว่าเหตุการณ์หนึ่งเกิดขึ้นและเสร็จก่อนอีกเหตุการณ์ในอดีต",
                "structure": "Subject + had + V3",
                "keywords": "before, after, already",
                "example": "She had finished homework before she ate dinner."
            },

            # Past Perfect Continuous
            "DURATION": {
                "tense": "Past Perfect Continuous",
                "thai_name": "Past Perfect Continuous - ทำมาก่อนในอดีต",
                "usage": "ใช้คู่กับ Past Simple เพื่อบอกสิ่งที่กำลังทำอยู่สักพักหนึ่งก่อนอีกสิ่งจะเกิดในอดีต",
                "structure": "Subject + had + been + V-ing",
                "keywords": "for, since, before",
                "example": "I had been waiting for 2 hours before he arrived."
            },

            # Future Simple
            "50PERC": {
                "tense": "Future Simple",
                "thai_name": "Future Simple - คาดการณ์ 50%",
                "usage": "สิ่งที่คาดจะเกิด หรือมีแนวโน้มในอนาคต (50%)",
                "structure": "Subject + will + V1",
                "keywords": "probably, maybe, I think",
                "example": "It will probably rain tomorrow."
            },
            "PROMISE": {
                "tense": "Future Simple",
                "thai_name": "Future Simple - สัญญา/เสนอ",
                "usage": "การให้คำสัญญา หรือเสนออะไรให้ใคร",
                "structure": "Subject + will + V1",
                "keywords": "promise, offer",
                "example": "I will help you with your homework."
            },
            "RIGHTNOW": {
                "tense": "Future Simple",
                "thai_name": "Future Simple - ตัดสินใจทันที",
                "usage": "สิ่งที่เพิ่งคิดว่าจะทำเดี๋ยวนั้น (ไม่ได้วางแผนว่าจะทำมาก่อน)",
                "structure": "Subject + will + V1",
                "keywords": "OK, I'll..., spontaneous decision",
                "example": "The doorbell is ringing. I'll answer it."
            },

            # Future Continuous
            "LONGFUTURE": {
                "tense": "Future Continuous",
                "thai_name": "Future Continuous - กำลังทำในอนาคต",
                "usage": "สิ่งที่คาดว่าน่าจะเกิดขึ้น คงจะทำอยู่ หรือวางแผนว่าจะทำ ณ เวลาหนึ่งในอนาคต",
                "structure": "Subject + will + be + V-ing",
                "keywords": "at ... tomorrow, this time next week",
                "example": "I will be studying at 8 PM tomorrow."
            },

            # Future Perfect
            "PREDICT": {
                "tense": "Future Perfect",
                "thai_name": "Future Perfect - จะเสร็จก่อน",
                "usage": "สิ่งที่คาดว่าคงจบ เสร็จสิ้น หรือครบเวลาแล้ว ณ เวลาหนึ่งในอนาคต",
                "structure": "Subject + will + have + V3",
                "keywords": "by, by the time",
                "example": "I will have finished by 5 PM."
            },

            # Future Perfect Continuous
            "WILLCONTINUEINFUTURE": {
                "tense": "Future Perfect Continuous",
                "thai_name": "Future Perfect Continuous - ทำต่อเนื่องในอนาคต",
                "usage": "สิ่งที่คาดว่าคงจบ เสร็จสิ้น หรือครบเวลาแล้ว ณ เวลาหนึ่งในอนาคต และจะคงสภาพหรือทำแบบนี้ต่อไปอีก",
                "structure": "Subject + will + have + been + V-ing",
                "keywords": "for, by the time",
                "example": "By next year, I will have been working here for 10 years."
            }
        }


class TyphoonTranslator:
    """Thai to English translation using Typhoon Translate 4B GGUF model"""
    def __init__(self):
        self.model = None
        self.model_path = "./models/typhoon-translate-4b-q4_k_m.gguf"
        
        # Try to load the GGUF model (CPU optimized)
        try:
            from llama_cpp import Llama
            
            if os.path.exists(self.model_path):
                self.model = Llama(
                    model_path=self.model_path,
                    verbose=False,
                    n_ctx=2048,        # Context length
                    n_threads=4,       # CPU threads (adjust based on your CPU)
                    n_batch=512,       # Batch size
                    n_gpu_layers=0,    # Force CPU usage (no GPU layers)
                    use_mlock=True,    # Lock model in RAM for faster access
                    use_mmap=True,     # Memory-mapped files for efficiency
                    f16_kv=False       # Use f32 for CPU (f16 is for GPU)
                )
                print("✓ Typhoon Translate GGUF model loaded successfully (CPU)")
            else:
                print(f"✗ GGUF model not found at {self.model_path}")
                print("  Using mock translations as fallback")
        except ImportError:
            print("✗ llama-cpp-python not installed. Using mock translations.")
        except Exception as e:
            print(f"✗ Error loading GGUF model: {e}")
            print("  Using mock translations as fallback")
    
    def translate(self, thai_text):
        """Translate Thai text to English"""
        if self.model:
            try:
                # Use proper prompt format for Typhoon
                prompt = f"<s>Translate Thai to English: {thai_text}\nEnglish:"
                
                response = self.model(
                    prompt,
                    max_tokens=80,  # Reduced for single-sentence focus
                    temperature=0.1,  # Lower temperature for consistent output
                    stop=["</s>", "\n", "Thai:"],  # Stop tokens
                    echo=False  # Don't echo the prompt
                )
                
                translation = response['choices'][0]['text'].strip()
                return translation
            except Exception as e:
                print(f"Translation error: {e}")
                # Fall back to mock translations
        
        # Mock translations as fallback
        translations = {
            "ฉันกินข้าวเช้าทุกวัน": "I eat breakfast every day.",
            "เมื่อวานฉันไปตลาด": "Yesterday I went to the market.",
            "พรุ่งนี้ฉันจะไปเรียน": "Tomorrow I will go to study."
        }
        return translations.get(thai_text, "I eat rice.")  # Default translation


class TenseClassifier:
    """Tense classification using XLM-RoBERTa hierarchical model"""
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_path = "./models/bert-tense-hier/best"
        self.device = "cpu"  # Force CPU usage
        
        # Label mappings
        self.id2coarse = {}
        self.id2fine = {}
        
        # Coarse-to-fine mapping to ensure consistency
        self.coarse_to_fine_mapping = {
            'Present': ['HABIT', 'FACT', 'TABLE', 'SAYING', 'HEADLINE', 'PLAN', 
                        'HAPPENING', 'NOWADAYS', 'SUREFUT', 'PROGRESS', 
                        'JUSTFIN', 'RESULT', 'EXP', 'SINCEFOR'],
            'Past': ['NORFIN', 'INTERRUPT', 'DOINGATSOMETIMEPAST', 'BEFOREPAST', 'DURATION'],
            'Future': ['50PERC', 'PROMISE', 'RIGHTNOW', 'LONGFUTURE', 'PREDICT', 'WILLCONTINUEINFUTURE']
        }
        
        # Tense definitions for human-readable labels
        self.tense_definitions = TenseTagDefinitions()
        
        # Try to load the BERT model
        try:
            if os.path.exists(self.model_path):
                self._load_model()
                print("✓ XLM-RoBERTa tense classifier loaded successfully")
            else:
                print(f"✗ BERT model not found at {self.model_path}")
                print("  Using mock classifications as fallback")
        except ImportError:
            print("✗ Transformers not installed. Using mock classifications.")
        except Exception as e:
            print(f"✗ Error loading BERT model: {e}")
            print("  Using mock classifications as fallback")
    
    def _load_model(self):
        """Load the BERT model and associated files"""
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        
        # Load configuration
        config = AutoConfig.from_pretrained(self.model_path)
        config.add_pooling_layer = False
        
        # Initialize model architecture
        self.model = XLMRHierClassifier(
            config=config,
            n_coarse=3,
            n_fine=25,
            coarse_w=0.3
        )
        
        # Load weights
        weights_path = os.path.join(self.model_path, "model.safetensors")
        weights = safe_load_file(weights_path)
        self.model.load_state_dict(weights)
        
        # Move to CPU and set to evaluation mode
        self.model.eval().to(self.device)
        
        # Load label mappings
        with open(os.path.join(self.model_path, "coarse_labels.json")) as f:
            self.id2coarse = json.load(f)
        with open(os.path.join(self.model_path, "fine_labels.json")) as f:
            self.id2fine = json.load(f)
    
    def classify(self, english_text, top_k=3):
        """Classify tense from English text"""
        if self.model and self.tokenizer:
            try:
                # Tokenize input
                inputs = self.tokenizer(english_text, return_tensors="pt").to(self.device)
                
                # Run inference
                with torch.inference_mode():
                    logits = self.model(**inputs)["logits"]
                    coarse_logits, fine_logits = logits
                
                # Convert to probabilities
                coarse_probs = F.softmax(coarse_logits, dim=1)
                
                # Get coarse prediction first
                coarse_topk = torch.topk(coarse_probs, k=min(top_k, len(self.id2coarse)), dim=1)
                coarse_pred = self.id2coarse[coarse_topk.indices[0][0].item()]
                
                # Constrain fine predictions based on coarse category
                # Create a mask for valid fine codes
                valid_fine_codes = self.coarse_to_fine_mapping.get(coarse_pred, [])
                fine_mask = torch.zeros_like(fine_logits[0])
                
                # Set mask to 1 for valid fine codes, -inf for invalid ones
                # Handle both dict and list formats for id2fine
                if isinstance(self.id2fine, dict):
                    fine_items = self.id2fine.items()
                else:
                    # If it's a list, convert to enumerate
                    fine_items = enumerate(self.id2fine)
                
                for i, fine_label in fine_items:
                    if fine_label in valid_fine_codes:
                        fine_mask[i] = 0
                    else:
                        fine_mask[i] = float('-inf')
                
                # Apply mask to fine logits
                masked_fine_logits = fine_logits + fine_mask.unsqueeze(0)
                
                # Get probabilities from masked logits
                fine_probs = F.softmax(masked_fine_logits, dim=1)
                
                # Get top predictions from constrained space
                fine_topk = torch.topk(fine_probs, k=min(top_k, len(valid_fine_codes)), dim=1)
                
                # Format results with human-readable labels
                fine_code = self.id2fine[fine_topk.indices[0][0].item()]
                fine_confidence = fine_topk.values[0][0].item()
                
                # Get human-readable fine label
                fine_info = self.tense_definitions.fine_definitions.get(fine_code, {})
                fine_readable = fine_info.get('thai_name', fine_code)
                
                return {
                    'coarse_label': coarse_pred,
                    'fine_label': fine_readable,
                    'fine_code': fine_code,
                    'confidence': fine_confidence,
                    'all_predictions': {
                        'coarse': [(self.id2coarse[idx.item()], prob.item()) 
                                 for idx, prob in zip(coarse_topk.indices[0], coarse_topk.values[0])],
                        'fine': [(self.id2fine[idx.item()], prob.item()) 
                               for idx, prob in zip(fine_topk.indices[0], fine_topk.values[0]) 
                               if self.id2fine[idx.item()] in valid_fine_codes]
                    }
                }
            except Exception as e:
                print(f"BERT classification error: {e}")
                # Fall back to mock classification
        
        # Mock classification as fallback
        if "will" in english_text.lower() or "tomorrow" in english_text.lower():
            return {
                'coarse_label': "Future",
                'fine_label': "Future Simple - คาดการณ์ 50%",
                'fine_code': "50PERC", 
                'confidence': 0.85,
                'all_predictions': {'coarse': [("Future", 0.85)], 'fine': [("50PERC", 0.85)]}
            }
        elif "yesterday" in english_text.lower() or "went" in english_text.lower():
            return {
                'coarse_label': "Past",
                'fine_label': "Past Simple - อดีทั่วไป",
                'fine_code': "NORFIN",
                'confidence': 0.85,
                'all_predictions': {'coarse': [("Past", 0.85)], 'fine': [("NORFIN", 0.85)]}
            }
        elif "every day" in english_text.lower():
            return {
                'coarse_label': "Present",
                'fine_label': "Present Simple - กิจวัตร/นิสัย",
                'fine_code': "HABIT",
                'confidence': 0.85,
                'all_predictions': {'coarse': [("Present", 0.85)], 'fine': [("HABIT", 0.85)]}
            }
        else:
            return {
                'coarse_label': "Present",
                'fine_label': "Present Simple - ข้อเท็จจริง",
                'fine_code': "FACT",
                'confidence': 0.80,
                'all_predictions': {'coarse': [("Present", 0.80)], 'fine': [("FACT", 0.80)]}
            }


class GrammarExplainer:
    """Grammar explanation using Typhoon 2.1 4B Instruct via Together AI API"""
    def __init__(self):
        # Initialize Together AI client
        self.client = None
        self.api_key = os.getenv('TOGETHER_API_KEY')
        self.model_name = "scb10x/scb10x-typhoon-2-1-gemma3-12b"
        
        # Initialize tense definitions for context
        self.tense_definitions = TenseTagDefinitions()
        
        # Initialize API client
        if Together:
            if self.api_key:
                try:
                    self.client = Together(api_key=self.api_key)
                    print("✓ Together AI client initialized successfully")
                except Exception as e:
                    print(f"✗ Error initializing Together AI client: {e}")
                    self.client = None
            else:
                print("⚠️ Warning: TOGETHER_API_KEY not found in environment. Using mock explanations.")
                self.client = None
        else:
            print("✗ Together package not available. Using mock explanations.")
    
    def explain(self, analysis_result):
        """Generate grammar explanation based on analysis using Together AI API"""
        thai_text = analysis_result.get('input_thai', '')
        translation = analysis_result.get('translation', '')
        analyzed_sentence = analysis_result.get('analyzed_sentence', translation)
        is_multi_sentence = analysis_result.get('is_multi_sentence', False)
        fine_code = analysis_result.get('fine_code', 'UNKNOWN')
        confidence = analysis_result.get('confidence', 0.0)
        
        if self.client:
            try:
                explanation = self._generate_explanation_api(
                    thai_text, translation, analyzed_sentence, is_multi_sentence, fine_code, confidence
                )
                return self._parse_explanation_sections(explanation)
            except Exception as e:
                print(f"API explanation failed: {e}")
                # Fall back to mock explanation
        
        # Mock explanation as fallback
        return self._generate_mock_explanation(analysis_result)
    
    def _generate_explanation_api(self, thai_text, english_translation, analyzed_sentence, is_multi_sentence, fine_label, confidence):
        """Generate explanation using Together AI API with enhanced context for sentence analysis"""
        # Get detailed tag definitions
        fine_def = self.tense_definitions.fine_definitions.get(fine_label, {})
        
        # Build tag explanation context
        tag_context = f"""
Tense ที่ตรวจพบ: {fine_label}
ประเภท: {fine_def.get('tense', 'Unknown')} - {fine_def.get('thai_name', '')}
การใช้งาน: {fine_def.get('usage', '')}
โครงสร้าง: {fine_def.get('structure', '')}
คำสัญญาณ: {fine_def.get('keywords', '')}
ตัวอย่าง: {fine_def.get('example', '')}
"""

        # Determine confidence tier and add appropriate instructions
        confidence_instruction = ""
        if confidence < 0.7:
            confidence_instruction = """
<confidence_note>
ระบบมีความมั่นใจต่ำ ({:.1%}) ในการจำแนก tense นี้ โปรดพิจารณาความเป็นไปได้อื่นๆ ด้วย
- อธิบายว่าทำไมประโยคนี้อาจตีความได้หลายแบบ
- เสนอ tense อื่นที่เป็นไปได้พร้อมเหตุผล
- ใช้คำว่า "อาจจะ", "น่าจะ", "มีความเป็นไปได้" ในการอธิบาย
</confidence_note>""".format(confidence)
        elif confidence < 0.9:
            confidence_instruction = """
<confidence_note>
ระบบมีความมั่นใจปานกลาง ({:.1%}) ในการจำแนก tense นี้
- ระบุว่ามี tense อื่นที่ใกล้เคียงที่อาจเป็นไปได้
- อธิบายความแตกต่างเล็กน้อยที่ทำให้เลือก tense นี้
</confidence_note>""".format(confidence)
        else:
            confidence_instruction = """
<confidence_note>
ระบบมีความมั่นใจสูง ({:.1%}) ในการจำแนก tense นี้
- อธิบายอย่างมั่นใจและชัดเจน
</confidence_note>""".format(confidence)

        # Use exact prompt structure from notebook 05 with Thai sections
        prompt_body = f"""<context>
คุณคือระบบวิเคราะห์ไวยากรณ์ภาษาอังกฤษสำหรับผู้เรียนไทย
คุณมีความรู้ลึกซึ้งเกี่ยวกับระบบ tense ในภาษาอังกฤษและความแตกต่างกับภาษาไทย
</context>

<tense_knowledge>
{tag_context}
</tense_knowledge>

{confidence_instruction}

<task>
วิเคราะห์การแปลประโยคและอธิบายการใช้ tense ที่เลือกอย่างละเอียด โดยคำนึงถึงระดับความมั่นใจของระบบ
</task>

<input>
ประโยคภาษาไทย: {thai_text}
การแปลภาษาอังกฤษ: {english_translation}
{f"ประโยคที่วิเคราะห์: {analyzed_sentence}" if is_multi_sentence else ""}
{f"หมายเหตุ: ระบบได้วิเคราะห์เฉพาะประโยคแรกเท่านั้น เนื่องจากพบหลายประโยค" if is_multi_sentence else ""}
Tense ที่ระบบตรวจพบ: {fine_label} (ความมั่นใจ: {confidence:.1%})
</input>

<requirements>
โปรดอธิบายโดยครอบคลุมประเด็นต่อไปนี้:

**1) วิเคราะห์ Tense ที่ใช้**
- อธิบาย tense ทางไวยากรณ์ที่ใช้ (เช่น Present Simple, Past Perfect)
- อธิบายการใช้งานในบริบทนี้โดยเฉพาะ
- โครงสร้างไวยากรณ์: {fine_def.get('structure', '')}
- หากความมั่นใจต่ำกว่า 90% ให้ระบุ tense อื่นที่อาจเป็นไปได้

**2) คำศัพท์ที่น่าสนใจ**
- เลือกคำศัพท์ / วลี ภาษาอังกฤษที่น่าสนใจจากประโยคมาหนึ่งคำ / วลี
- อธิบายว่าทำไมถึงเลือกใช้คำนั้นในการแปล

**3) ข้อผิดพลาดที่พบบ่อย**
- ผู้เรียนไทยมักใช้ tense ที่ใช้ในประโยคผิดอย่างไร
- วิธีจำง่าย ๆ
- หากความมั่นใจต่ำ ให้เน้นการสังเกตคำสัญญาณเพื่อแยกแยะ tense
</requirements>

<format>
- ใช้ภาษาไทยที่เข้าใจง่าย
- อธิบายเป็นขั้นตอน มีหัวข้อชัดเจน
- ยกตัวอย่างประกอบ
- เน้นสิ่งที่ผู้เรียนไทยควรระวัง
- **เริ่มต้นด้วยการวิเคราะห์ทันที**
- **ใช้รูปแบบวิชาการ ไม่ใช่รูปแบบสนทนา**
- **ห้ามเขียนหัวข้ออื่น ๆ ที่ไม่อยู่ใน Requirement**
- **ใช้รูปแบบหัวข้อเป็น: **1) วิเคราะห์ Tense ที่ใช้** **2) คำศัพท์ที่น่าสนใจ** **3) ข้อผิดพลาดที่พบบ่อย****

**การจัดรูปแบบข้อความ:**
- แต่ละประโยคต้องแยกด้วยการขึ้นบรรทัดใหม่
- ใช้ **ตัวหนา** สำหรับคำสำคัญ เช่น **Present Simple:** **โครงสร้าง:** **ตัวอย่าง:**
- แยกแต่ละหัวข้อย่อยด้วยการขึ้นบรรทัดใหม่ 2 ครั้ง
- ใส่ช่องว่างหลังเครื่องหมายจุลภาค จุด และเครื่องหมายโคลอน
- เขียนให้อ่านง่าย ไม่รวมประโยคยาวๆ เป็นก้อนเดียว
</format>"""

        messages = [
            {
                "role": "system",
                "content": """คุณคือระบบวิเคราะห์ไวยากรณ์ภาษาอังกฤษสำหรับผู้เรียนไทย คุณให้คำอธิบายที่ตรงประเด็น กระชับ และเป็นวิชาการ

กฎสำคัญ:
- อธิบาย TENSE ทางไวยากรณ์ (Present Simple, Past Perfect ฯลฯ) ไม่ใช่รหัสจัดหมวดหมู่
- ไม่ใช้คำทักทาย คำลา หรือบทนำ
- เริ่มต้นด้วยการวิเคราะห์ทันที
- ใช้ภาษาวิชาการที่เข้าใจง่าย
- ตอบตรงประเด็นตามหัวข้อที่กำหนด
- ใช้รูปแบบหัวข้อ **1) วิเคราะห์ Tense ที่ใช้** **2) คำศัพท์ที่น่าสนใจ** **3) ข้อผิดพลาดที่พบบ่อย** เท่านั้น

กฎเกี่ยวกับความมั่นใจ:
- ความมั่นใจ >90%: อธิบายอย่างชัดเจนและมั่นใจ
- ความมั่นใจ 70-90%: ระบุว่า "ระบบค่อนข้างมั่นใจ" และเสนอ tense ใกล้เคียงที่อาจเป็นไปได้
- ความมั่นใจ <70%: ใช้คำว่า "อาจจะ", "น่าจะ", "มีความเป็นไปได้" และเสนอทางเลือกอื่นๆ

กฎการจัดรูปแบบ (สำคัญมาก):
- แต่ละประโยคขึ้นบรรทัดใหม่แยกจากกัน
- ใช้ **ตัวหนา** สำหรับคำสำคัญและหัวข้อย่อย
- เว้นบรรทัดว่างระหว่างหัวข้อย่อย
- ไม่เขียนประโยคยาวต่อเนื่องกันเป็นก้อน
- ใส่ช่องว่างหลังเครื่องหมายจุลภาคและจุด"""
            },
            {"role": "user", "content": prompt_body}
        ]

        # Call Together AI API with same parameters as notebook 05
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=600,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1
        )

        return response.choices[0].message.content.strip()
    
    def _parse_explanation_sections(self, explanation):
        """Parse explanation into Thai sections using regex with enhanced formatting"""
        sections = {}
        
        # Regex patterns for Thai sections with ** formatting
        patterns = {
            'tense_analysis': r'\*\*1\)\s*วิเคราะห์\s*Tense\s*ที่ใช้\*\*\s*(.*?)(?=\*\*2\)|$)',
            'vocabulary': r'\*\*2\)\s*คำศัพท์ที่น่าสนใจ\*\*\s*(.*?)(?=\*\*3\)|$)', 
            'common_mistakes': r'\*\*3\)\s*ข้อผิดพลาดที่พบบ่อย\*\*\s*(.*?)$'
        }
        
        for section_name, pattern in patterns.items():
            match = re.search(pattern, explanation, re.DOTALL | re.IGNORECASE)
            if match:
                raw_content = match.group(1).strip()
                # Apply enhanced formatting to the section content
                formatted_content = self._format_explanation_content(raw_content)
                sections[section_name] = formatted_content
            else:
                sections[section_name] = "ส่วนนี้ไม่สามารถแยกได้"
        
        return {
            'raw_explanation': explanation,
            'parsed_sections': sections
        }
    
    def _format_explanation_content(self, content):
        """Enhanced formatting for explanation content to improve readability"""
        if not content:
            return content
        
        # Clean up the content first
        content = content.strip()
        
        # 1. Add line breaks after sentences that end with periods
        content = re.sub(r'\.(\s*)([ก-๙])', r'.\n\n\2', content)
        
        # 2. Add line breaks before bullet points and numbered lists
        content = re.sub(r'(\s*)([•\-\*]\s+)', r'\n\2', content)
        
        # 3. Add line breaks before bold/emphasized text patterns
        content = re.sub(r'(\s*)(\*\*[^*]+\*\*)', r'\n\n\2', content)
        
        # 4. Add spacing around colons for definitions
        content = re.sub(r'(\*\*[^*]+\*\*:)', r'\1\n', content)
        
        # 5. Add line breaks before "โครงสร้าง" and similar structural words
        structure_words = ['โครงสร้าง', 'ตัวอย่าง', 'การใช้งาน', 'คำสัญญาณ', 'วิธีจำ']
        for word in structure_words:
            content = re.sub(f'(\s*)(\*\*{word}[^*]*\*\*)', r'\n\n\2', content)
        
        # 6. Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 7. Remove leading/trailing whitespace
        content = content.strip()
        
        # 8. Ensure proper spacing after colons in definitions
        content = re.sub(r':\s*([ก-๙])', r': \1', content)
        
        return content
    
    def _generate_mock_explanation(self, analysis_result):
        """Generate mock explanation as fallback"""
        coarse = analysis_result.get('coarse_label', 'UNKNOWN')
        confidence = analysis_result.get('confidence', 0.85)
        
        # Add confidence-aware prefix based on tier
        confidence_prefix = ""
        if confidence < 0.7:
            confidence_prefix = "**หมายเหตุ:** ระบบมีความมั่นใจต่ำ ({}%) ในการจำแนก tense นี้\n\n".format(int(confidence * 100))
        elif confidence < 0.9:
            confidence_prefix = "**หมายเหตุ:** ระบบค่อนข้างมั่นใจ ({}%) ในการจำแนก tense นี้\n\n".format(int(confidence * 100))
        
        if "Present" in coarse:
            explanation = confidence_prefix + """**1) วิเคราะห์ Tense ที่ใช้**
ประโยคนี้ใช้ Present Simple Tense เพื่อแสดงการกระทำที่เป็นกิจวัตรประจำ โครงสร้าง: Subject + V1"""
            
            if confidence < 0.9:
                explanation += "\n\nอย่างไรก็ตาม ประโยคนี้อาจเป็น Present Continuous ได้เช่นกัน หากมีบริบทที่แสดงถึงการกระทำที่กำลังเกิดขึ้น"
            
            explanation += """

**2) คำศัพท์ที่น่าสนใจ**
คำว่า "every day" เป็นคำสัญญาณที่บ่งบอกถึงความเป็นประจำ

**3) ข้อผิดพลาดที่พบบ่อย**
ผู้เรียนไทยมักลืมเติม s/es ให้กับประธานเอกพจน์บุรุษที่ 3"""
            
            if confidence < 0.7:
                explanation += "\n\nควรสังเกตคำสัญญาณในประโยคเพื่อแยกแยะ tense ได้แม่นยำมากขึ้น"
                
        elif "Past" in coarse:
            explanation = confidence_prefix + """**1) วิเคราะห์ Tense ที่ใช้**
ประโยคนี้ใช้ Past Simple Tense เพื่อแสดงการกระทำที่เกิดขึ้นในอดีต โครงสร้าง: Subject + V2"""

            if confidence < 0.9:
                explanation += "\n\nทั้งนี้ อาจเป็น Past Continuous หรือ Present Perfect ได้ ขึ้นอยู่กับบริบท"

            explanation += """

**2) คำศัพท์ที่น่าสนใจ**
คำว่า "yesterday" เป็นคำสัญญาณบอกเวลาในอดีต

**3) ข้อผิดพลาดที่พบบ่อย**
ผู้เรียนไทยมักใช้ verb ช่องที่ 1 แทนช่องที่ 2 ในอดีต"""

            if confidence < 0.7:
                explanation += "\n\nแนะนำให้ดูคำสัญญาณเวลาเพื่อยืนยัน tense ที่ถูกต้อง"
                
        else:
            explanation = confidence_prefix + """**1) วิเคราะห์ Tense ที่ใช้**
ประโยคนี้ใช้ Future Simple Tense เพื่อแสดงการกระทำที่จะเกิดขึ้นในอนาคต โครงสร้าง: Subject + will + V1"""

            if confidence < 0.9:
                explanation += "\n\nอาจเป็น Present Continuous (be going to) สำหรับแผนการในอนาคตที่วางไว้แล้ว"

            explanation += """

**2) คำศัพท์ที่น่าสนใจ**
คำว่า "will" เป็นคำช่วยที่บ่งบอกถึงอนาคต

**3) ข้อผิดพลาดที่พบบ่อย**
ผู้เรียนไทยมักใช้ going to และ will สับสน"""

            if confidence < 0.7:
                explanation += "\n\nควรพิจารณาบริบทว่าเป็นการตัดสินใจเฉพาะหน้า (will) หรือแผนที่วางไว้ (going to)"
        
        return self._parse_explanation_sections(explanation)


class ModelManager:
    """Manages all models and coordinates the pipeline"""
    def __init__(self):
        self.translator = None
        self.classifier = None
        self.explainer = None
        self._load_models()
    
    def _load_models(self):
        """Load all models with error handling"""
        try:
            self.translator = TyphoonTranslator()
            print("✓ Translator loaded successfully")
        except Exception as e:
            print(f"✗ Translation model failed to load: {e}")
        
        try:
            self.classifier = TenseClassifier()
            print("✓ Classifier loaded successfully")
        except Exception as e:
            print(f"✗ Classification model failed to load: {e}")
        
        try:
            self.explainer = GrammarExplainer()
            print("✓ Explainer loaded successfully")
        except Exception as e:
            print(f"✗ Explanation model failed to load: {e}")
    
    def full_pipeline(self, thai_text, progress_callback=None, user_id=None, log_performance=True, performance_callback=None):
        """Run full NLP pipeline on Thai text with optional progress callbacks and performance logging"""
        result = {"input_thai": thai_text}
        
        # Initialize timing variables
        translation_time = None
        classification_time = None
        explanation_time = None
        success = True
        error_stage = None
        
        # Step 1: Translation
        if progress_callback:
            progress_callback(1, 33, "Translating...", "กำลังแปล...")
        
        if self.translator:
            try:
                start_time = time.time()
                full_translation = self.translator.translate(thai_text)
                result["translation"] = full_translation
                translation_time = time.time() - start_time
                
                # Extract first sentence for classification
                first_sentence, is_multi_sentence = extract_first_sentence(full_translation)
                result["analyzed_sentence"] = first_sentence
                result["is_multi_sentence"] = is_multi_sentence
                
            except Exception as e:
                translation_time = time.time() - start_time if 'start_time' in locals() else 0
                result["translation"] = f"Translation failed: {str(e)}"
                result["analyzed_sentence"] = ""
                result["is_multi_sentence"] = False
                success = False
                error_stage = "translation"
        else:
            result["translation"] = "Translation service unavailable"
            result["analyzed_sentence"] = ""
            result["is_multi_sentence"] = False
            success = False
            error_stage = "translation"
        
        # Step 2: Tense Classification
        if progress_callback:
            progress_callback(2, 66, "Classifying tense...", "กำลังจำแนกกาล...")
        
        if self.classifier and "analyzed_sentence" in result and result["analyzed_sentence"] and success:
            try:
                start_time = time.time()
                # Classify only the first sentence
                classification_result = self.classifier.classify(result["analyzed_sentence"])
                classification_time = time.time() - start_time
                
                result["coarse_label"] = classification_result["coarse_label"]
                result["fine_label"] = classification_result["fine_label"]
                result["fine_code"] = classification_result["fine_code"]
                result["confidence"] = classification_result["confidence"]
                result["all_predictions"] = classification_result["all_predictions"]
            except Exception as e:
                classification_time = time.time() - start_time if 'start_time' in locals() else 0
                result["coarse_label"] = "ERROR"
                result["fine_label"] = f"Classification failed: {str(e)}"
                result["fine_code"] = "ERROR"
                result["confidence"] = 0.0
                result["all_predictions"] = {}
                success = False
                error_stage = "classification"
        else:
            result["coarse_label"] = "UNKNOWN"
            result["fine_label"] = "Classification service unavailable"
            result["fine_code"] = "UNKNOWN"
            result["confidence"] = 0.0
            result["all_predictions"] = {}
            if success:  # Only mark as failed if it wasn't already failed
                success = False
                error_stage = "classification"
        
        # Step 3: Grammar Explanation
        if progress_callback:
            progress_callback(3, 100, "Generating explanation...", "กำลังสร้างคำอธิบาย...")
        
        if self.explainer and success:
            try:
                start_time = time.time()
                result["explanation"] = self.explainer.explain(result)
                explanation_time = time.time() - start_time
            except Exception as e:
                explanation_time = time.time() - start_time if 'start_time' in locals() else 0
                result["explanation"] = f"[SECTION 1: Context Cues]\nExplanation generation failed: {str(e)}"
                success = False
                error_stage = "explanation"
        else:
            result["explanation"] = "[SECTION 1: Context Cues]\nExplanation service unavailable"
            if success:  # Only mark as failed if it wasn't already failed
                success = False
                error_stage = "explanation"
        
        # Log performance if enabled and callback is provided
        if log_performance and performance_callback and callable(performance_callback):
            try:
                input_length = len(thai_text)
                performance_callback(
                    user_id=user_id,
                    input_length=input_length,
                    translation_time=translation_time,
                    classification_time=classification_time,
                    explanation_time=explanation_time,
                    success=success,
                    error_stage=error_stage
                )
            except Exception as e:
                # Don't let performance logging break the pipeline
                print(f"Performance logging failed: {e}")
        
        return result


# For backward compatibility with existing code expecting Hybrid4BSystem
Hybrid4BSystem = ModelManager