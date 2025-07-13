from flask import Flask, render_template, request, flash, Response, jsonify
import re
import json
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
        
        # Handle the new explanation format
        explanation = result.get('explanation', '')
        if isinstance(explanation, dict) and 'parsed_sections' in explanation:
            # New format with parsed sections
            explanation_sections = {
                'section_1': {
                    'title': 'วิเคราะห์ Tense ที่ใช้',
                    'content': explanation['parsed_sections'].get('tense_analysis', 'ส่วนนี้ไม่สามารถแยกได้')
                },
                'section_2': {
                    'title': 'คำศัพท์ที่น่าสนใจ',
                    'content': explanation['parsed_sections'].get('vocabulary', 'ส่วนนี้ไม่สามารถแยกได้')
                },
                'section_3': {
                    'title': 'ข้อผิดพลาดที่พบบ่อย',
                    'content': explanation['parsed_sections'].get('common_mistakes', 'ส่วนนี้ไม่สามารถแยกได้')
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

@app.route('/predict_stream', methods=['POST'])
def predict_stream():
    """Stream progress updates during prediction using Server-Sent Events"""
    # Get Thai text from request OUTSIDE the generator function
    try:
        data = request.get_json()
        thai_text = data.get('thai_text', '').strip() if data else ''
    except Exception as e:
        return Response(f"data: {json.dumps({'error': f'Request parsing error: {str(e)}'})}\n\n", 
                       mimetype='text/plain')
    
    if not thai_text:
        return Response(f"data: {json.dumps({'error': 'Please enter a Thai sentence.'})}\n\n", 
                       mimetype='text/plain')
    
    def generate(text_input):
        try:
            print(f"🏁 Starting pipeline generation for: '{text_input}'")
            
            # Progress tracking variables to store yielded progress
            yielded_updates = []
            
            def progress_callback(step, progress, message, message_thai):
                """Callback that yields progress updates during pipeline execution"""
                update = {
                    'step': step,
                    'progress': progress,
                    'message': message,
                    'message_thai': message_thai
                }
                yielded_updates.append(f"data: {json.dumps(update)}\n\n")
                print(f"📊 Progress callback: Step {step} - {progress}% - {message}")
            
            # Run the full pipeline with progress callbacks
            print("🔄 Running full pipeline...")
            result = model_manager.full_pipeline(text_input, progress_callback=progress_callback)
            print(f"✅ Pipeline completed. Result keys: {list(result.keys()) if result else 'None'}")
            
            # Yield all the progress updates that were collected
            print(f"📤 Yielding {len(yielded_updates)} progress updates")
            for i, update in enumerate(yielded_updates):
                print(f"📨 Yielding update {i+1}/{len(yielded_updates)}")
                yield update
            
            # Complete - send final result
            completion_event = {'complete': True, 'result': result}
            completion_json = json.dumps(completion_event)
            completion_message = f"data: {completion_json}\n\n"
            
            print(f"🎉 Sending completion event (length: {len(completion_message)} chars)")
            print(f"🔍 Completion preview: {completion_message[:200]}...")
            
            yield completion_message
            print("✅ All events yielded successfully")
            
        except Exception as e:
            error_message = f"data: {json.dumps({'error': f'An error occurred: {str(e)}'})}\n\n"
            print(f"❌ Pipeline error: {e}")
            print(f"📤 Yielding error: {error_message}")
            yield error_message
    
    return Response(generate(thai_text), mimetype='text/plain', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'text/plain; charset=utf-8'
    })

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
    app.run(host='0.0.0.0', port = 5000, debug = True)