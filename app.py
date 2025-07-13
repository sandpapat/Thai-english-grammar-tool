from flask import Flask, render_template, request, flash
import re
from app.pipeline import ModelManager

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
        
        # Parse the explanation sections
        explanation_sections = parse_explanation(result.get('explanation', ''))
        
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
            'content': section_content
        }
    
    # If no sections found, return the full text as a single section
    if not sections:
        sections['section_1'] = {
            'title': 'Explanation',
            'content': explanation_text
        }
    
    return sections

if __name__ == '__main__':
    app.run(debug=True)