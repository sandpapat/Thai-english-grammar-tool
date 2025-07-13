"""
NLP Pipeline with separated model management
Models:
1. Typhoon Translate 4B (GGUF via llama-cpp)
2. XLM-RoBERTa (Transformers)
3. Typhoon 2.1 4B Instruct (Transformers)
"""

import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import XLMRobertaModel, AutoConfig, PreTrainedModel, AutoTokenizer
from safetensors.torch import load_file as safe_load_file


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
                    max_tokens=200,
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
                fine_probs = F.softmax(fine_logits, dim=1)
                
                # Get top predictions
                coarse_topk = torch.topk(coarse_probs, k=min(top_k, len(self.id2coarse)), dim=1)
                fine_topk = torch.topk(fine_probs, k=min(top_k, len(self.id2fine)), dim=1)
                
                # Format results with human-readable labels
                coarse_pred = self.id2coarse[coarse_topk.indices[0][0].item()]
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
                               for idx, prob in zip(fine_topk.indices[0], fine_topk.values[0])]
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
    """Grammar explanation using Typhoon 2.1 4B Instruct"""
    def __init__(self):
        # In production, initialize transformers model here
        # from transformers import AutoModelForCausalLM, AutoTokenizer
        # self.model = AutoModelForCausalLM.from_pretrained("path/to/typhoon-2.1-instruct")
        # self.tokenizer = AutoTokenizer.from_pretrained("path/to/typhoon-2.1-instruct")
        self.model = None  # Mock for now
    
    def explain(self, analysis_result):
        """Generate grammar explanation based on analysis"""
        # Mock implementation - replace with actual model call
        # In production: 
        # prompt = self._create_prompt(analysis_result)
        # inputs = self.tokenizer(prompt, return_tensors="pt")
        # outputs = self.model.generate(**inputs, max_length=500)
        # explanation = self.tokenizer.decode(outputs[0])
        
        coarse = analysis_result.get('coarse_label', 'UNKNOWN')
        fine = analysis_result.get('fine_label', 'UNKNOWN')
        translation = analysis_result.get('translation', '')
        
        # Mock explanation based on tense
        if coarse == "PRESENT" and fine == "HABIT":
            explanation = """[SECTION 1: Context Cues]
The phrase "every day" (ทุกวัน) is a clear temporal marker indicating habitual action. This type of time expression signals that the action happens regularly or repeatedly.

[SECTION 2: Tense Decision]
The combination of the habitual marker "every day" with the action verb leads to Present Simple tense in English. This tense is used for routines, habits, and repeated actions.

[SECTION 3: Grammar Tips]
In English, habitual actions use Present Simple: Subject + base verb (+ s/es for 3rd person singular). Thai doesn't mark tense on verbs, so English tense must be inferred from context clues like ทุกวัน (every day)."""
        
        elif coarse == "PAST":
            explanation = """[SECTION 1: Context Cues]
The word "yesterday" (เมื่อวาน) is a definite past time marker. This clearly indicates the action happened in the past.

[SECTION 2: Tense Decision]
With a specific past time reference, English requires Past Simple tense. The verb changes to its past form.

[SECTION 3: Grammar Tips]
Past Simple in English: Subject + past verb form. Regular verbs add -ed, while irregular verbs have special forms (go→went, eat→ate)."""
        
        elif coarse == "FUTURE":
            explanation = """[SECTION 1: Context Cues]
The word "tomorrow" (พรุ่งนี้) indicates future time. The Thai particle จะ also marks future intention.

[SECTION 2: Tense Decision]
Future time markers require future tense in English, typically using "will" + base verb.

[SECTION 3: Grammar Tips]
Future Simple in English: Subject + will + base verb. Thai จะ often corresponds to English "will"."""
        
        else:
            explanation = """[SECTION 1: Context Cues]
No specific time markers found in the sentence.

[SECTION 2: Tense Decision]
Without time markers, Present Simple is used as the default tense.

[SECTION 3: Grammar Tips]
When translating from Thai without time markers, consider the context to determine the appropriate English tense."""
        
        return explanation


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
    
    def full_pipeline(self, thai_text):
        """Run full NLP pipeline on Thai text"""
        result = {"input_thai": thai_text}
        
        # Step 1: Translation
        if self.translator:
            try:
                result["translation"] = self.translator.translate(thai_text)
            except Exception as e:
                result["translation"] = f"Translation failed: {str(e)}"
        else:
            result["translation"] = "Translation service unavailable"
        
        # Step 2: Tense Classification
        if self.classifier and "translation" in result:
            try:
                classification_result = self.classifier.classify(result["translation"])
                result["coarse_label"] = classification_result["coarse_label"]
                result["fine_label"] = classification_result["fine_label"]
                result["fine_code"] = classification_result["fine_code"]
                result["confidence"] = classification_result["confidence"]
                result["all_predictions"] = classification_result["all_predictions"]
            except Exception as e:
                result["coarse_label"] = "ERROR"
                result["fine_label"] = f"Classification failed: {str(e)}"
                result["fine_code"] = "ERROR"
                result["confidence"] = 0.0
                result["all_predictions"] = {}
        else:
            result["coarse_label"] = "UNKNOWN"
            result["fine_label"] = "Classification service unavailable"
            result["fine_code"] = "UNKNOWN"
            result["confidence"] = 0.0
            result["all_predictions"] = {}
        
        # Step 3: Grammar Explanation
        if self.explainer:
            try:
                result["explanation"] = self.explainer.explain(result)
            except Exception as e:
                result["explanation"] = f"[SECTION 1: Context Cues]\nExplanation generation failed: {str(e)}"
        else:
            result["explanation"] = "[SECTION 1: Context Cues]\nExplanation service unavailable"
        
        return result


# For backward compatibility with existing code expecting Hybrid4BSystem
Hybrid4BSystem = ModelManager