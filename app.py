from flask import Flask, render_template, request, flash, Response, jsonify
import re
import json
from app.pipeline import ModelManager

def format_explanation_content(content):
    """Format explanation content for better readability"""
    if not content:
        return content
    
    # Clean up the raw content
    content = content.strip()
    
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    
    # Fix broken bold patterns like "**Text•*" or "**Text*"
    content = re.sub(r'\*\*([^*]+?)[•\*]*\*+', r'**\1**', content)
    
    # Clean up scattered bullet symbols and newlines
    # Remove standalone bullet symbols and asterisks on their own lines
    content = re.sub(r'\n\s*[•\*]\s*\n', '\n', content)
    content = re.sub(r'^[•\*]\s*$', '', content, flags=re.MULTILINE)
    
    # Fix patterns where content is broken across lines
    # Join lines that end with "**Text" and start with bullet symbols
    content = re.sub(r'(\*\*[^*\n]+)\n\s*[•\*]\s*\n\s*\*', r'\1**', content)
    
    # Clean up multiple consecutive newlines
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Process line by line for proper structure
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle bold text
        line = re.sub(r'\*\*([^*]+)\*\*', r'<strong class="text-primary">\1</strong>', line)
        
        # Check if it's a structural header (ends with colon)
        if (line.endswith(':') and 
            (any(word in line for word in ['Continuous', 'Simple', 'Perfect', 'โครงสร้าง', 'ตัวอย่าง', 'วิธี']) or
             line.count(' ') <= 3)):
            formatted_lines.append(f'<h6 class="text-secondary mt-3 mb-2">{line}</h6>')
        else:
            # Regular content line
            formatted_lines.append(line)
    
    # Join lines with proper spacing
    result = '<br>\n'.join(formatted_lines) if formatted_lines else content
    
    # Wrap in a paragraph if it doesn't start with HTML
    if result and not result.startswith('<'):
        result = f'<p class="mb-3">{result}</p>'
    elif result.startswith('<br>'):
        result = f'<p class="mb-3">{result[4:]}</p>'  # Remove leading <br>
    
    return result

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = 'your-secret-key-here-change-in-production'

# Initialize the model manager
model_manager = ModelManager()

@app.route('/')
def index():
    """Homepage with Thai text input form"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Process Thai text through NLP pipeline"""
    try:
        # Get Thai text from form
        thai_text = request.form.get('thai_text', '').strip()
        
        if not thai_text:
            flash('Please enter a Thai sentence.', 'error')
            return render_template('index.html')
        
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
    app.run(host='0.0.0.0', port = 5000, debug = True)