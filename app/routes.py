"""
Main application routes
"""
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
    max_tokens=500,
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