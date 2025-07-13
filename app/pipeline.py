"""
NLP Pipeline with separated model management
Models:
1. Typhoon Translate 4B (GGUF via llama-cpp)
2. XLM-RoBERTa (Transformers)
3. Typhoon 2.1 4B Instruct (Transformers)
"""

import os

class TyphoonTranslator:
    """Thai to English translation using Typhoon Translate 4B GGUF model"""
    def __init__(self):
        self.model = None
        self.model_path = "./models/typhoon-translate-4b-q4_k_m.gguf"
        
        # Try to load the GGUF model
        try:
            from llama_cpp import Llama
            
            if os.path.exists(self.model_path):
                self.model = Llama(
                    model_path=self.model_path,
                    verbose=False,
                    n_ctx=2048,     # Context length
                    n_threads=4,    # CPU threads
                    n_batch=512     # Batch size
                )
                print("✓ Typhoon Translate GGUF model loaded successfully")
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
    """Tense classification using XLM-RoBERTa"""
    def __init__(self):
        # In production, initialize transformers model here
        # from transformers import AutoModelForSequenceClassification, AutoTokenizer
        # self.model = AutoModelForSequenceClassification.from_pretrained("path/to/model")
        # self.tokenizer = AutoTokenizer.from_pretrained("path/to/model")
        self.model = None  # Mock for now
    
    def classify(self, english_text):
        """Classify tense from English text"""
        # Mock implementation - replace with actual model call
        # In production: 
        # inputs = self.tokenizer(english_text, return_tensors="pt")
        # outputs = self.model(**inputs)
        # predictions = process_outputs(outputs)
        
        # Mock logic based on keywords
        if "will" in english_text.lower() or "tomorrow" in english_text.lower():
            return "FUTURE", "SIMPLE"
        elif "yesterday" in english_text.lower() or "went" in english_text.lower():
            return "PAST", "SIMPLE"
        elif "every day" in english_text.lower():
            return "PRESENT", "HABIT"
        else:
            return "PRESENT", "SIMPLE"


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
                coarse, fine = self.classifier.classify(result["translation"])
                result["coarse_label"] = coarse
                result["fine_label"] = fine
            except Exception as e:
                result["coarse_label"] = "ERROR"
                result["fine_label"] = str(e)
        else:
            result["coarse_label"] = "UNKNOWN"
            result["fine_label"] = "UNKNOWN"
        
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