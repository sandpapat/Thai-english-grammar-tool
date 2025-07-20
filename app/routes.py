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
        
        # Simple synchronous performance logging (fast database insert)
        def log_performance_data(**kwargs):
            try:
                from flask import has_app_context
                if has_app_context():
                    from .models import SystemPerformance
                    SystemPerformance.log_performance(**kwargs)
                else:
                    print("Performance logging skipped: No Flask app context")
            except Exception as e:
                print(f"Performance logging failed: {e}")
        
        # Run the pipeline with user ID for performance logging
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        result = model_manager.full_pipeline(
            thai_text, 
            user_id=user_id, 
            performance_callback=log_performance_data
        )
        
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


@main_bp.route('/api/average-response-time', methods=['GET'])
def get_average_response_time():
    """API endpoint to get current average response time for countdown timer"""
    try:
        from .models import SystemPerformance
        stats = SystemPerformance.get_performance_stats()
        
        # Get average total time, default to 10 seconds if no data
        avg_total_time = stats.get('avg_total_time', 10.0)
        
        # Add small buffer for better UX (show slightly less time than actual)
        display_time = max(5.0, avg_total_time * 0.9)  # 90% of actual time, minimum 5 seconds
        
        # Get input length factor for dynamic estimation
        avg_input_length = stats.get('avg_input_length', 50.0)
        
        return jsonify({
            'average_time': round(display_time, 1),
            'total_requests': stats.get('total_requests', 0),
            'success_rate': stats.get('success_rate', 0),
            'average_input_length': round(avg_input_length, 0)
        })
    
    except Exception as e:
        # Fallback to default values if database not available
        return jsonify({
            'average_time': 8.0,  # Conservative default
            'total_requests': 0,
            'success_rate': 0,
            'average_input_length': 50
        })


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