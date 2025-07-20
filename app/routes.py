"""
Main application routes
"""
import time
from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from .pipeline import ModelManager
from .validation import InputValidator
from .utils import format_explanation_content, parse_explanation
from .data import get_performance_data

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize the model manager and input validator
model_manager = ModelManager()
input_validator = InputValidator(
    max_tokens=100,
    min_thai_percentage=0.8,
    enable_profanity_filter=True
)


@main_bp.route('/')
def index():
    """Homepage with Thai text input form"""
    return render_template('index.html')


@main_bp.route('/predict', methods=['POST'])
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
        
        # Run the pipeline with user ID for performance logging
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        result = model_manager.full_pipeline(thai_text, user_id=user_id)
        
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


@main_bp.route('/predict-stream', methods=['POST'])
@login_required
def predict_stream():
    """Process Thai text through NLP pipeline with real-time progress updates via SSE"""
    import json
    from flask import Response
    
    try:
        # Get Thai text from form
        thai_text = request.form.get('thai_text', '').strip()
        
        # Validate input
        validation_result = input_validator.validate_input(thai_text)
        
        # Handle validation errors
        if not validation_result['is_valid']:
            def error_stream():
                error_message = validation_result['errors'][0]['message']['th'] if validation_result['errors'] else 'Invalid input'
                yield f"data: {json.dumps({'error': error_message})}\n\n"
            return Response(error_stream(), mimetype='text/event-stream')
        
        # Handle validation warnings
        warning_messages = []
        for warning in validation_result['warnings']:
            warning_messages.append(warning['message']['th'])
        
        def generate_progress():
            """Generator function to stream progress updates"""
            
            # Send initial progress with any warnings
            initial_data = {
                'stage': 0, 
                'progress': 5, 
                'message': 'Starting pipeline...', 
                'message_thai': 'เริ่มต้นการประมวลผล...',
                'warnings': warning_messages
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            try:
                # Get user ID for performance logging
                user_id = current_user.id if current_user and current_user.is_authenticated else None
                
                # Manual pipeline execution with real-time SSE streaming
                # This replicates model_manager.full_pipeline() but with real-time yields
                
                result = {"input_thai": thai_text}
                
                # Initialize timing variables for performance logging
                translation_time = None
                classification_time = None
                explanation_time = None
                success = True
                error_stage = None
                
                # Step 1: Translation  
                progress_data = {
                    'stage': 1,
                    'progress': 5,
                    'message': 'Translating...',
                    'message_thai': 'กำลังแปล...'
                }
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                if model_manager.translator:
                    try:
                        start_time = time.time()
                        result["translation"] = model_manager.translator.translate(thai_text)
                        translation_time = time.time() - start_time
                        progress_data = {
                            'stage': 1,
                            'progress': 10,
                            'message': 'Translation complete',
                            'message_thai': 'การแปลเสร็จสิ้น'
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    except Exception as e:
                        translation_time = time.time() - start_time if 'start_time' in locals() else 0
                        result["translation"] = f"Translation failed: {str(e)}"
                        success = False
                        error_stage = "translation"
                else:
                    result["translation"] = "Translation service unavailable"
                    success = False
                    error_stage = "translation"
                
                # Step 2: Tense Classification
                progress_data = {
                    'stage': 2,
                    'progress': 15,
                    'message': 'Classifying tense...',
                    'message_thai': 'กำลังจำแนกกาล...'
                }
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                if model_manager.classifier and "translation" in result and success:
                    try:
                        start_time = time.time()
                        classification_result = model_manager.classifier.classify(result["translation"])
                        classification_time = time.time() - start_time
                        
                        result["coarse_label"] = classification_result["coarse_label"]
                        result["fine_label"] = classification_result["fine_label"]
                        result["fine_code"] = classification_result["fine_code"]
                        result["confidence"] = classification_result["confidence"]
                        result["all_predictions"] = classification_result["all_predictions"]
                        
                        progress_data = {
                            'stage': 2,
                            'progress': 20,
                            'message': 'Tense classification complete',
                            'message_thai': 'การจำแนกกาลเสร็จสิ้น'
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
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
                
                # Step 3: Grammar Explanation (This takes ~16-17 seconds!)
                progress_data = {
                    'stage': 3,
                    'progress': 25,
                    'message': 'Generating explanation...',
                    'message_thai': 'กำลังสร้างคำอธิบาย...'
                }
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                if model_manager.explainer and success:
                    try:
                        # This is the long-running call (6-7 seconds)
                        start_time = time.time()
                        result["explanation"] = model_manager.explainer.explain(result)
                        explanation_time = time.time() - start_time
                        
                        # Only show 100% AFTER the explanation is actually generated
                        progress_data = {
                            'stage': 3,
                            'progress': 100,
                            'message': 'Explanation complete',
                            'message_thai': 'คำอธิบายเสร็จสิ้น'
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    except Exception as e:
                        explanation_time = time.time() - start_time if 'start_time' in locals() else 0
                        result["explanation"] = f"[SECTION 1: Context Cues]\nExplanation generation failed: {str(e)}"
                        success = False
                        error_stage = "explanation"
                        
                        # Show completion even on error
                        progress_data = {
                            'stage': 3,
                            'progress': 100,
                            'message': 'Explanation failed',
                            'message_thai': 'คำอธิบายล้มเหลว'
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                else:
                    result["explanation"] = "[SECTION 1: Context Cues]\nExplanation service unavailable"
                    if success:  # Only mark as failed if it wasn't already failed
                        success = False
                        error_stage = "explanation"
                    
                    # Show completion for unavailable service
                    progress_data = {
                        'stage': 3,
                        'progress': 100,
                        'message': 'Explanation unavailable',
                        'message_thai': 'คำอธิบายไม่พร้อมใช้งาน'
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n"
                
                # Log performance
                try:
                    from .models import SystemPerformance
                    input_length = len(thai_text)
                    SystemPerformance.log_performance(
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
                
                # Handle the explanation format (same as original predict route)
                if result:
                    explanation = result.get('explanation', '')
                    if isinstance(explanation, dict) and 'parsed_sections' in explanation:
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
                        explanation_sections = parse_explanation(explanation)
                    
                    # Send final result with parsed explanation
                    final_data = {
                        'stage': 4,
                        'progress': 100,
                        'message': 'Complete!',
                        'message_thai': 'เสร็จสิ้น!',
                        'complete': True,
                        'result': result,
                        'explanation_sections': explanation_sections
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                
            except Exception as e:
                error_data = {
                    'error': f'Pipeline error: {str(e)}',
                    'stage': -1,
                    'progress': 0
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        response = Response(generate_progress(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering
        return response
        
    except Exception as e:
        def error_stream():
            yield f"data: {json.dumps({'error': f'Server error: {str(e)}'})}\n\n"
        return Response(error_stream(), mimetype='text/event-stream')


@main_bp.route('/validate', methods=['POST'])
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


@main_bp.route('/tenses')
def tenses():
    """Display tense usage explanations"""
    return render_template('tenses.html')


@main_bp.route('/about')
def about():
    """Display about us page"""
    return render_template('about.html')


@main_bp.route('/performance')
def performance():
    """Display model performance metrics"""
    performance_data = get_performance_data()
    return render_template('performance.html', performance=performance_data)


@main_bp.route('/classifier-performance')
def classifier_performance():
    """Display BERT classifier isolated test results"""
    performance_data = get_performance_data()
    return render_template('classifier_performance.html', performance=performance_data)


@main_bp.route('/pipeline-performance')
def pipeline_performance():
    """Display full pipeline evaluation results"""
    performance_data = get_performance_data(pipeline_mode=True)
    return render_template('pipeline_performance.html', performance=performance_data)


@main_bp.route('/system-performance')
def system_performance():
    """Display real-time system performance metrics"""
    try:
        from .models import SystemPerformance
        performance_stats = SystemPerformance.get_performance_stats()
        return render_template('system_performance.html', stats=performance_stats)
    except Exception as e:
        flash(f'Error loading performance data: {str(e)}', 'error')
        return render_template('system_performance.html', stats=None)