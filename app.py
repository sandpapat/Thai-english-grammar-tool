from flask import Flask, render_template, request, flash, Response, jsonify
import re
import json
import os
from app.pipeline import ModelManager
from app.validation import InputValidator
from app.models import db, Pseudocode
from app.auth import auth_bp
from flask_login import LoginManager, login_required, current_user

def format_explanation_content(content):
    """Format explanation content for better readability"""
    if not content:
        return content
    
    # Clean up the raw content
    content = content.strip()
    
    # Remove HTML tags first
    content = re.sub(r'<[^>]+>', '', content)
    
    # Fix broken bold patterns like "**Text•*" or "**Text*"
    content = re.sub(r'\*\*([^*]+?)[•\*]*\*+', r'**\1**', content)
    
    # Clean up scattered bullet symbols and newlines (but preserve actual bullet points)
    content = re.sub(r'\n\s*[•\*]\s*\n', '\n', content)
    content = re.sub(r'^[•\*]\s*$', '', content, flags=re.MULTILINE)
    
    # Fix patterns where content is broken across lines
    content = re.sub(r'(\*\*[^*\n]+)\n\s*[•\*]\s*\n\s*\*', r'\1**', content)
    
    # Clean up multiple consecutive newlines
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # First pass: identify and mark special keywords for highlighting
    # Common time markers and grammar keywords
    keyword_patterns = [
        (r'\b(yesterday|today|tomorrow|now|then)\b', 'time-marker'),
        (r'\b(last week|last month|last year|next week|next month|next year)\b', 'time-marker'),
        (r'\b(ago|before|after|since|until)\b', 'time-marker'),
        (r'\b(always|usually|often|sometimes|never|rarely)\b', 'frequency-marker'),
        (r'\b(every day|every week|every month|every year)\b', 'frequency-marker'),
        (r'\b(Subject|Verb|Object|V1|V2|V3|Past Simple|Present Simple|Future Simple)\b', 'grammar-term'),
        (r'\b(market|school|hospital|restaurant|office|home)\b', 'place-marker')
    ]
    
    # Apply keyword highlighting
    for pattern, css_class in keyword_patterns:
        content = re.sub(pattern, rf'<span class="keyword-highlight {css_class}">\1</span>', content, flags=re.IGNORECASE)
    
    # Process line by line for proper structure
    lines = content.split('\n')
    formatted_lines = []
    in_paragraph = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            continue
        
        # Handle bold text (but preserve highlighted keywords inside)
        line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)
        
        # Check if it's a bullet point
        if line.startswith('* ') and len(line) > 2:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            bullet_content = line[2:].strip()
            formatted_lines.append(f'<li class="thai-bullet mb-2">{bullet_content}</li>')
        
        # Check if it's a structural header
        elif (line.endswith(':') and 
              (any(word in line for word in ['โครงสร้าง', 'ตัวอย่าง', 'วิธี', 'คำศัพท์', 'Subject', 'Verb']) or
               line.count(' ') <= 3)):
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            formatted_lines.append(f'<h6 class="grammar-header mt-3 mb-2">{line}</h6>')
        
        # Check if line starts with Thai example indicators
        elif line.startswith('ตัวอย่าง:') or line.startswith('เช่น:'):
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            formatted_lines.append(f'<p class="example-text mb-2">{line}</p>')
        
        # Regular content line
        else:
            if not in_paragraph and not line.startswith('<'):
                formatted_lines.append('<p class="explanation-paragraph mb-3">')
                in_paragraph = True
            
            # Add line with proper spacing
            if in_paragraph and len(formatted_lines) > 0 and not formatted_lines[-1].endswith('>'):
                formatted_lines.append('<br>')
            formatted_lines.append(line)
    
    # Close any open paragraph
    if in_paragraph:
        formatted_lines.append('</p>')
    
    # Group consecutive list items into proper <ul> tags
    final_html = []
    in_list = False
    
    for line in formatted_lines:
        if line.startswith('<li'):
            if not in_list:
                final_html.append('<ul class="thai-list">')
                in_list = True
            final_html.append('  ' + line)
        else:
            if in_list:
                final_html.append('</ul>')
                in_list = False
            final_html.append(line)
    
    # Close any remaining list
    if in_list:
        final_html.append('</ul>')
    
    # Join all HTML elements
    result = '\n'.join(final_html)
    
    # Final cleanup - ensure no empty paragraphs
    result = re.sub(r'<p[^>]*>\s*</p>', '', result)
    
    return result

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pseudocodes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return Pseudocode.query.get(int(user_id))

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Initialize the model manager and input validator
model_manager = ModelManager()
input_validator = InputValidator(
    max_tokens=500,
    min_thai_percentage=0.8,
    enable_profanity_filter=True
)

@app.route('/')
def index():
    """Homepage with Thai text input form"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """Process Thai text through NLP pipeline"""
    try:
        # Get Thai text from form
        thai_text = request.form.get('thai_text', '').strip()
        
        # Validate input
        validation_result = input_validator.validate_input(thai_text)
        
        # Handle validation errors
        if not validation_result['is_valid']:
            for error in validation_result['errors']:
                flash(error['message']['th'], 'error')
            return render_template('index.html')
        
        # Handle validation warnings
        for warning in validation_result['warnings']:
            flash(warning['message']['th'], 'warning')
        
        # Run the pipeline
        result = model_manager.full_pipeline(thai_text)
        
        # Handle the new explanation format
        explanation = result.get('explanation', '')
        if isinstance(explanation, dict) and 'parsed_sections' in explanation:
            # New format with parsed sections - apply formatting
            explanation_sections = {
                'section_1': {
                    'title': 'วิเคราะห์ Tense ที่ใช้',
                    'content': format_explanation_content(explanation['parsed_sections'].get('tense_analysis', 'ส่วนนี้ไม่สามารถแยกได้'))
                },
                'section_2': {
                    'title': 'คำศัพท์ที่น่าสนใจ',
                    'content': format_explanation_content(explanation['parsed_sections'].get('vocabulary', 'ส่วนนี้ไม่สามารถแยกได้'))
                },
                'section_3': {
                    'title': 'ข้อผิดพลาดที่พบบ่อย',
                    'content': format_explanation_content(explanation['parsed_sections'].get('common_mistakes', 'ส่วนนี้ไม่สามารถแยกได้'))
                }
            }
        else:
            # Legacy format - try to parse as before
            explanation_sections = parse_explanation(explanation)
        
        return render_template('result.html', 
                               result=result,
                               explanation_sections=explanation_sections)
    
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return render_template('index.html')


@app.route('/validate', methods=['POST'])
def validate_input():
    """API endpoint for real-time input validation"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        validation_result = input_validator.get_validation_summary(text)
        
        return jsonify(validation_result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tenses')
def tenses():
    """Display tense usage explanations"""
    return render_template('tenses.html')

@app.route('/performance')
def performance():
    """Display model performance metrics"""
    # Actual performance data from test results
    performance_data = {
        'translator': {
            'name': 'Typhoon Translate 4B',
            'type': 'GGUF via llama-cpp',
            'metrics': {
                'BLEU Score': 'TBD',
                'Average Latency': 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'classifier': {
            'name': 'XLM-RoBERTa',
            'type': 'Transformers',
            'metrics': {
                'Accuracy': '94.7%',
                'Macro F1 Score': '91.3%',
                'Weighted F1 Score': '94.6%'
            },
            'confusion_matrix': {
                'Past': {'Past': 99.77, 'Present': 0.23, 'Future': 0.00},
                'Present': {'Past': 0.34, 'Present': 99.49, 'Future': 0.17},
                'Future': {'Past': 0.00, 'Present': 0.00, 'Future': 100.00}
            },
            'top_performing_labels': [
                {'label': 'BEFOREPAST', 'f1': 1.000},
                {'label': 'DURATION', 'f1': 1.000},
                {'label': 'JUSTFIN', 'f1': 1.000},
                {'label': 'LONGFUTURE', 'f1': 1.000},
                {'label': 'SINCEFOR', 'f1': 1.000},
                {'label': 'WILLCONTINUEINFUTURE', 'f1': 1.000}
            ],
            'challenging_labels': [
                {'label': 'NOWADAYS', 'f1': 0.308},
                {'label': 'PROMISE', 'f1': 0.600},
                {'label': 'RIGHTNOW', 'f1': 0.824},
                {'label': 'SAYING', 'f1': 0.833}
            ]
        },
        'explainer': {
            'name': 'Typhoon 2.1 4B Instruct',
            'type': 'Transformers',
            'metrics': {
                'Quality Score': 'TBD',
                'Average Latency': 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'pipeline': {
            'total_latency': 'TBD ms',
            'success_rate': 'TBD%',
            'requests_processed': 0
        }
    }
    
    return render_template('performance.html', performance=performance_data)

@app.route('/classifier-performance')
def classifier_performance():
    """Display BERT classifier isolated test results"""
    # Use the same performance data structure for consistency
    performance_data = {
        'translator': {
            'name': 'Typhoon Translate 4B',
            'type': 'GGUF via llama-cpp',
            'metrics': {
                'BLEU Score': 'TBD',
                'Average Latency': 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'classifier': {
            'name': 'XLM-RoBERTa',
            'type': 'Transformers',
            'metrics': {
                'Accuracy': '94.7%',
                'Macro F1 Score': '91.3%',
                'Weighted F1 Score': '94.6%'
            },
            'confusion_matrix': {
                'Past': {'Past': 99.77, 'Present': 0.23, 'Future': 0.00},
                'Present': {'Past': 0.34, 'Present': 99.49, 'Future': 0.17},
                'Future': {'Past': 0.00, 'Present': 0.00, 'Future': 100.00}
            },
            'top_performing_labels': [
                {'label': 'BEFOREPAST', 'f1': 1.000},
                {'label': 'DURATION', 'f1': 1.000},
                {'label': 'JUSTFIN', 'f1': 1.000},
                {'label': 'LONGFUTURE', 'f1': 1.000},
                {'label': 'SINCEFOR', 'f1': 1.000},
                {'label': 'WILLCONTINUEINFUTURE', 'f1': 1.000}
            ],
            'challenging_labels': [
                {'label': 'NOWADAYS', 'f1': 0.308},
                {'label': 'PROMISE', 'f1': 0.600},
                {'label': 'RIGHTNOW', 'f1': 0.824},
                {'label': 'SAYING', 'f1': 0.833}
            ]
        },
        'explainer': {
            'name': 'Typhoon 2.1 4B Instruct',
            'type': 'Transformers',
            'metrics': {
                'Quality Score': 'TBD',
                'Average Latency': 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'pipeline': {
            'total_latency': 'TBD ms',
            'success_rate': 'TBD%',
            'requests_processed': 0
        }
    }
    
    return render_template('classifier_performance.html', performance=performance_data)

@app.route('/pipeline-performance')
def pipeline_performance():
    """Display full pipeline evaluation results"""
    # Pipeline performance data from model_evaluation_analysis.md
    performance_data = {
        'translator': {
            'name': 'Typhoon Translate 4B',
            'type': 'GGUF via llama-cpp',
            'metrics': {
                'BLEU Score': 'TBD',
                'Average Latency': '1.20s',
                'Memory Usage': 'TBD GB'
            }
        },
        'classifier': {
            'name': 'XLM-RoBERTa',
            'type': 'Transformers',
            'metrics': {
                'Accuracy': '94.7%',
                'Macro F1 Score': '91.3%',
                'Weighted F1 Score': '94.6%'
            },
            'confusion_matrix': {
                'Past': {'Past': 99.77, 'Present': 0.23, 'Future': 0.00},
                'Present': {'Past': 0.34, 'Present': 99.49, 'Future': 0.17},
                'Future': {'Past': 0.00, 'Present': 0.00, 'Future': 100.00}
            },
            'top_performing_labels': [
                {'label': 'BEFOREPAST', 'f1': 1.000},
                {'label': 'DURATION', 'f1': 1.000},
                {'label': 'JUSTFIN', 'f1': 1.000},
                {'label': 'LONGFUTURE', 'f1': 1.000},
                {'label': 'SINCEFOR', 'f1': 1.000},
                {'label': 'WILLCONTINUEINFUTURE', 'f1': 1.000}
            ],
            'challenging_labels': [
                {'label': 'NOWADAYS', 'f1': 0.308},
                {'label': 'PROMISE', 'f1': 0.600},
                {'label': 'RIGHTNOW', 'f1': 0.824},
                {'label': 'SAYING', 'f1': 0.833}
            ]
        },
        'explainer': {
            'name': 'Typhoon 2.1 4B Instruct',
            'type': 'Transformers',
            'metrics': {
                'Quality Score': 'TBD',
                'Average Latency': '10.26s',
                'Memory Usage': 'TBD GB'
            }
        },
        'pipeline': {
            'total_latency': '11.47s',
            'success_rate': 'TBD%',
            'requests_processed': 96,
            'note': 'Timing excludes cold start response'
        }
    }
    
    return render_template('pipeline_performance.html', performance=performance_data)

def parse_explanation(explanation_text):
    """Parse explanation into sections based on [SECTION X: ...] markers"""
    sections = {}
    
    # Pattern to match sections
    pattern = r'\[SECTION (\d+): ([^\]]+)\](.*?)(?=\[SECTION|\Z)'
    matches = re.findall(pattern, explanation_text, re.DOTALL)
    
    for match in matches:
        section_num = match[0]
        section_title = match[1].strip()
        section_content = match[2].strip()
        sections[f'section_{section_num}'] = {
            'title': section_title,
            'content': format_explanation_content(section_content)
        }
    
    # If no sections found, return the full text as a single section
    if not sections:
        sections['section_1'] = {
            'title': 'Explanation',
            'content': format_explanation_content(explanation_text)
        }
    
    return sections

if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port = 5000, debug = True)