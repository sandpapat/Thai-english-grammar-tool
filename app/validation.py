"""
Input validation module for Thai language text
Provides comprehensive validation for user input including:
- Token length limits
- Thai language detection
- Sentence boundary detection
- Basic profanity filtering
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional


class TokenCounter:
    """Handles token counting for Thai text with configurable limits"""
    
    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens
        
    def count_tokens(self, text: str) -> Dict[str, int]:
        """Count various text metrics"""
        if not text:
            return {
                'characters': 0,
                'words': 0,
                'tokens': 0,
                'sentences': 0
            }
        
        # Character count (excluding spaces)
        char_count = len(text.replace(' ', ''))
        
        # Simple word count (split by spaces and punctuation)
        words = re.findall(r'[^\s\u0020-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E\u0E2F\u0E46\u0E4F\u0E5A\u0E5B]+', text)
        word_count = len(words)
        
        # Token count (approximation: characters/3 for Thai + word count)
        thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
        token_count = (thai_chars // 3) + word_count
        
        # Sentence count
        sentence_count = self._count_sentences(text)
        
        return {
            'characters': char_count,
            'words': word_count,
            'tokens': token_count,
            'sentences': sentence_count
        }
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences using Thai and English punctuation"""
        # Thai and English sentence endings
        sentence_endings = r'[.!?ฯ]+'
        sentences = re.split(sentence_endings, text)
        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def validate_length(self, text: str) -> Dict[str, any]:
        """Validate text length against limits"""
        metrics = self.count_tokens(text)
        
        return {
            'is_valid': metrics['tokens'] <= self.max_tokens,
            'token_count': metrics['tokens'],
            'max_tokens': self.max_tokens,
            'usage_percentage': (metrics['tokens'] / self.max_tokens) * 100,
            'metrics': metrics
        }


class ThaiLanguageDetector:
    """Detects Thai language content and provides warnings for mixed languages"""
    
    def __init__(self, min_thai_percentage: float = 0.8):
        self.min_thai_percentage = min_thai_percentage
        
    def analyze_language(self, text: str) -> Dict[str, any]:
        """Analyze language composition of text"""
        if not text:
            return {
                'thai_percentage': 0,
                'is_primarily_thai': False,
                'character_counts': {'thai': 0, 'english': 0, 'other': 0, 'total': 0}
            }
        
        # Count character types
        thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - thai_chars - english_chars - text.count(' ')
        total_chars = len(text.replace(' ', ''))
        
        thai_percentage = (thai_chars / total_chars) * 100 if total_chars > 0 else 0
        
        return {
            'thai_percentage': thai_percentage,
            'is_primarily_thai': thai_percentage >= (self.min_thai_percentage * 100),
            'character_counts': {
                'thai': thai_chars,
                'english': english_chars,
                'other': other_chars,
                'total': total_chars
            }
        }
    
    def validate_thai_content(self, text: str) -> Dict[str, any]:
        """Validate that text is primarily Thai"""
        analysis = self.analyze_language(text)
        
        return {
            'is_valid': analysis['is_primarily_thai'],
            'thai_percentage': analysis['thai_percentage'],
            'min_required': self.min_thai_percentage * 100,
            'warning_message': self._get_language_warning(analysis) if not analysis['is_primarily_thai'] else None
        }
    
    def _get_language_warning(self, analysis: Dict) -> Dict[str, str]:
        """Generate warning message for mixed language content"""
        if analysis['character_counts']['english'] > analysis['character_counts']['thai']:
            return {
                'en': 'Warning: Input appears to be primarily English. For best results, please use Thai text.',
                'th': 'คำเตือน: ข้อความที่ป้อนดูเหมือนจะเป็นภาษาอังกฤษเป็นหลัก กรุณาใช้ข้อความภาษาไทยเพื่อผลลัพธ์ที่ดีที่สุด'
            }
        else:
            return {
                'en': 'Warning: Mixed language detected. For optimal performance, use primarily Thai text.',
                'th': 'คำเตือn: พบภาษาผสม กรุณาใช้ข้อความภาษาไทยเป็นหลักเพื่อประสิทธิภาพที่ดีที่สุด'
            }


class SentenceBoundaryDetector:
    """Detects sentence boundaries and validates single sentence input"""
    
    def __init__(self):
        # Thai and English sentence ending patterns
        self.sentence_pattern = r'[.!?ฯ]+(?:\s|$)'
        
    def count_sentences(self, text: str) -> int:
        """Count number of sentences in text"""
        if not text:
            return 0
        
        # Split by sentence endings
        sentences = re.split(self.sentence_pattern, text)
        # Filter out empty strings and whitespace-only strings
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def validate_single_sentence(self, text: str) -> Dict[str, any]:
        """Validate that input contains only one sentence"""
        sentence_count = self.count_sentences(text)
        
        return {
            'is_single_sentence': sentence_count <= 1,
            'sentence_count': sentence_count,
            'warning_message': self._get_sentence_warning(sentence_count) if sentence_count > 1 else None
        }
    
    def _get_sentence_warning(self, count: int) -> Dict[str, str]:
        """Generate warning for multiple sentences"""
        return {
            'en': f'Notice: {count} sentences detected. For best analysis, consider using one sentence at a time.',
            'th': f'แจ้งเตือน: พบ {count} ประโยค เพื่อการวิเคราะห์ที่ดีที่สุด ควรใช้ประโยคเดียวในแต่ละครั้ง'
        }


class ProfanityFilter:
    """Basic profanity detection and filtering"""
    
    def __init__(self):
        # Basic profanity patterns (using placeholder approach)
        # In production, this would be loaded from a secure configuration
        self.thai_profanity_patterns = [
            # Add Thai profanity patterns here
            # Using regex patterns for flexibility
            r'ห[ีิ]*[ย]',  # Example pattern structure
        ]
        
        self.english_profanity_patterns = [
            # Add English profanity patterns here
            r'\b(damn|hell)\b',  # Example mild profanity
        ]
    
    def contains_profanity(self, text: str) -> bool:
        """Check if text contains profanity"""
        text_lower = text.lower()
        
        # Check Thai patterns
        for pattern in self.thai_profanity_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check English patterns
        for pattern in self.english_profanity_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def validate_content(self, text: str) -> Dict[str, any]:
        """Validate that text doesn't contain profanity"""
        has_profanity = self.contains_profanity(text)
        
        return {
            'is_valid': not has_profanity,
            'contains_profanity': has_profanity,
            'error_message': self._get_profanity_error() if has_profanity else None
        }
    
    def _get_profanity_error(self) -> Dict[str, str]:
        """Generate error message for profanity detection"""
        return {
            'en': 'Invalid content detected. Please use appropriate language.',
            'th': 'พบเนื้อหาที่ไม่เหมาะสม กรุณาใช้ภาษาที่เหมาะสม'
        }


class InputValidator:
    """Main validation class that coordinates all validation checks"""
    
    def __init__(self, 
                 max_tokens: int = 500,
                 min_thai_percentage: float = 0.8,
                 enable_profanity_filter: bool = True):
        self.token_counter = TokenCounter(max_tokens)
        self.language_detector = ThaiLanguageDetector(min_thai_percentage)
        self.sentence_detector = SentenceBoundaryDetector()
        self.profanity_filter = ProfanityFilter() if enable_profanity_filter else None
        
    def validate_input(self, text: str) -> Dict[str, any]:
        """Perform comprehensive validation on input text"""
        if not text or not text.strip():
            return {
                'is_valid': False,
                'errors': [{
                    'type': 'empty_input',
                    'message': {
                        'en': 'Please enter some text.',
                        'th': 'กรุณาใส่ข้อความ'
                    }
                }],
                'warnings': [],
                'metrics': {}
            }
        
        text = text.strip()
        errors = []
        warnings = []
        metrics = {}
        
        # 1. Token length validation
        length_result = self.token_counter.validate_length(text)
        metrics['length'] = length_result
        
        if not length_result['is_valid']:
            errors.append({
                'type': 'token_limit_exceeded',
                'message': {
                    'en': f'Text is too long ({length_result["token_count"]} tokens). Maximum allowed is {length_result["max_tokens"]} tokens.',
                    'th': f'ข้อความยาวเกินไป ({length_result["token_count"]} โทเค็น) ความยาวสูงสุดคือ {length_result["max_tokens"]} โทเค็น'
                }
            })
        
        # 2. Thai language validation
        thai_result = self.language_detector.validate_thai_content(text)
        metrics['language'] = thai_result
        
        if not thai_result['is_valid'] and thai_result['warning_message']:
            warnings.append({
                'type': 'mixed_language',
                'message': thai_result['warning_message']
            })
        
        # 3. Sentence boundary validation
        sentence_result = self.sentence_detector.validate_single_sentence(text)
        metrics['sentences'] = sentence_result
        
        if not sentence_result['is_single_sentence'] and sentence_result['warning_message']:
            warnings.append({
                'type': 'multiple_sentences',
                'message': sentence_result['warning_message']
            })
        
        # 4. Profanity filtering
        if self.profanity_filter:
            profanity_result = self.profanity_filter.validate_content(text)
            metrics['profanity'] = profanity_result
            
            if not profanity_result['is_valid']:
                errors.append({
                    'type': 'inappropriate_content',
                    'message': profanity_result['error_message']
                })
        
        # Determine overall validity
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'metrics': metrics,
            'text_stats': {
                'original_length': len(text),
                'token_count': length_result['token_count'],
                'thai_percentage': thai_result['thai_percentage'],
                'sentence_count': sentence_result['sentence_count']
            }
        }
    
    def get_validation_summary(self, text: str) -> Dict[str, any]:
        """Get a quick validation summary for frontend display"""
        result = self.validate_input(text)
        
        return {
            'is_valid': result['is_valid'],
            'has_warnings': len(result['warnings']) > 0,
            'token_count': result['text_stats']['token_count'],
            'token_limit': self.token_counter.max_tokens,
            'usage_percentage': (result['text_stats']['token_count'] / self.token_counter.max_tokens) * 100,
            'thai_percentage': result['text_stats']['thai_percentage'],
            'sentence_count': result['text_stats']['sentence_count']
        }