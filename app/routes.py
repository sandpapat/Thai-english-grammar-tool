"""
Main application routes
"""
import time
from flask import Blueprint, render_template, request, flash, jsonify, session
from flask_login import login_required, current_user
from .pipeline import ModelManager
from .validation import InputValidator
from .utils import format_explanation_content, parse_explanation
from .data import get_performance_data
from .rate_limiter import rate_limit, get_rate_limit_info
from .models import UserActivity

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
@rate_limit
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
        
        # Log translation activity
        session_token = session.get('session_token')
        UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='translation',
            session_token=session_token,
            details={
                'input_length': len(thai_text),
                'has_multiple_sentences': validation_result.get('text_stats', {}).get('sentence_count', 1) > 1
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
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


@main_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    try:
        from .models import db
        from .rate_limiter import rate_limiter
        
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Get system stats
        rate_stats = rate_limiter.get_stats()
        
        # Check model manager status
        model_status = {
            'translator': model_manager.translator is not None,
            'classifier': model_manager.classifier is not None,
            'explainer': model_manager.explainer is not None
        }
        
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'connected',
            'models': model_status,
            'rate_limiter': rate_stats,
            'all_models_loaded': all(model_status.values())
        }
        
        # Return appropriate status code
        status_code = 200 if health_data['all_models_loaded'] else 503
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 503


@main_bp.route('/api/rate-limit-info')
def rate_limit_info():
    """Get current rate limit status for user"""
    try:
        info = get_rate_limit_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/user-analytics')
@login_required
def user_analytics():
    """Display user-specific analytics dashboard"""
    try:
        from .models import UserActivity, UserSession
        
        # Get user analytics data
        user_stats = UserActivity.get_user_stats(current_user.id, days=30)
        
        # Get current session info
        session_token = session.get('session_token')
        current_session = None
        if session_token:
            current_session = UserSession.query.filter_by(
                session_token=session_token,
                is_active=True
            ).first()
        
        # Session information
        session_info = {
            'current_session_start': current_session.created_at if current_session else None,
            'last_activity': current_session.last_activity if current_session else None,
            'session_duration': None
        }
        
        if current_session:
            duration = current_session.last_activity - current_session.created_at
            session_info['session_duration'] = duration.total_seconds() / 60  # minutes
        
        return render_template(
            'user_analytics.html',
            user_stats=user_stats,
            session_info=session_info,
            user=current_user
        )
    except Exception as e:
        flash(f'Error loading analytics data: {str(e)}', 'error')
        return render_template('user_analytics.html', user_stats=None, session_info=None, user=current_user)


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


@main_bp.route('/api/submit-rating', methods=['POST'])
@login_required
def submit_rating():
    """Submit an enhanced multi-criteria rating for proficient users"""
    try:
        # Check if user is proficient
        if not current_user.is_proficient():
            return jsonify({
                'success': False,
                'error': 'Only proficient users can submit ratings'
            }), 403
        
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields for new multi-criteria rating
        required_fields = ['input_thai', 'translation_text', 'translation_accuracy', 
                          'translation_fluency', 'explanation_quality', 'educational_value']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate all rating values
        rating_fields = {
            'translation_accuracy': int(data['translation_accuracy']),
            'translation_fluency': int(data['translation_fluency']),
            'explanation_quality': int(data['explanation_quality']),
            'educational_value': int(data['educational_value'])
        }
        
        for field, value in rating_fields.items():
            if not (1 <= value <= 5):
                return jsonify({
                    'success': False,
                    'error': f'{field} must be between 1 and 5'
                }), 400
        
        # Validate issue tags (optional)
        issue_tags = data.get('issue_tags', [])
        if issue_tags and not isinstance(issue_tags, list):
            return jsonify({
                'success': False,
                'error': 'issue_tags must be an array'
            }), 400
        
        # Create the rating with new multi-criteria structure
        from .models import Rating, db, UserActivity
        
        rating = Rating.create_rating(
            user_id=current_user.id,
            input_thai=data['input_thai'],
            translation_text=data['translation_text'],
            translation_accuracy=rating_fields['translation_accuracy'],
            translation_fluency=rating_fields['translation_fluency'],
            explanation_quality=rating_fields['explanation_quality'],
            educational_value=rating_fields['educational_value'],
            issue_tags=issue_tags if issue_tags else None,
            comments=data.get('comments', '').strip() or None
        )
        
        # Log feedback activity with new detailed tracking
        session_token = session.get('session_token')
        UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='feedback',
            session_token=session_token,
            details={
                'rating_id': rating.id,
                'rating_type': 'multi_criteria',
                'translation_accuracy': rating_fields['translation_accuracy'],
                'translation_fluency': rating_fields['translation_fluency'],
                'explanation_quality': rating_fields['explanation_quality'],
                'educational_value': rating_fields['educational_value'],
                'issue_tags_count': len(issue_tags) if issue_tags else 0,
                'has_comments': bool(data.get('comments', '').strip())
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Detailed rating submitted successfully',
            'rating_id': rating.id
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while submitting your rating'
        }), 500


@main_bp.route('/api/extend-session', methods=['POST'])
@login_required
def extend_session():
    """Extend user session to prevent timeout"""
    try:
        from .models import UserSession
        
        session_token = session.get('session_token')
        if not session_token:
            return jsonify({
                'success': False,
                'error': 'No session token found'
            }), 400
        
        # Update session activity
        user_session, status = UserSession.validate_session(session_token, max_idle_minutes=15)
        
        if user_session:
            # Log session extension activity
            UserActivity.log_activity(
                user_id=current_user.id,
                activity_type='session_extended',
                session_token=session_token,
                details={'extension_method': 'manual'},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            return jsonify({
                'success': True,
                'message': 'Session extended successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session invalid or expired'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to extend session'
        }), 500


@main_bp.route('/api/track-activity', methods=['POST'])
@login_required
def track_activity():
    """Track user activity for analytics (lightweight endpoint)"""
    try:
        data = request.get_json()
        if not data or 'activity_type' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing activity type'
            }), 400
        
        activity_type = data.get('activity_type')
        activity_data = data.get('data', {})
        
        # Only track certain activity types
        allowed_types = ['page_view', 'page_leave', 'form_submit', 'session_warning']
        if activity_type not in allowed_types:
            return jsonify({
                'success': False,
                'error': 'Invalid activity type'
            }), 400
        
        # Log the activity
        session_token = session.get('session_token')
        UserActivity.log_activity(
            user_id=current_user.id,
            activity_type=activity_type,
            session_token=session_token,
            details=activity_data,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Activity tracked'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to track activity'
        }), 500