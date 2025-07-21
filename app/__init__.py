"""
Flask application factory and configuration
"""
import os
from flask import Flask, session, request, redirect, url_for
from flask_login import LoginManager, current_user, logout_user
from .models import db
from .auth import auth_bp


def create_app(config_name=None):
    """
    Application factory pattern for Flask app creation
    
    Args:
        config_name: Configuration name (development, testing, production)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Load configuration directly
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pseudocodes.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuration based on environment
    if config_name == 'testing':
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
    elif config_name == 'production' or os.environ.get('FLASK_ENV') == 'production':
        app.config['DEBUG'] = False
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_COOKIE_DOMAIN'] = '.thaislate.ai'
    else:
        app.config['DEBUG'] = True
    
    # Model configuration
    app.config['MAX_TOKENS'] = 100
    app.config['MIN_THAI_PERCENTAGE'] = 0.8
    app.config['ENABLE_PROFANITY_FILTER'] = True
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import Pseudocode
        return Pseudocode.query.get(int(user_id))
    
    # Session validation middleware (idle timeout check)
    @app.before_request
    def validate_session():
        """Validate session on each request and check for idle timeout"""
        from .models import UserSession, UserActivity
        
        # Skip validation for certain routes
        skip_routes = ['auth.login', 'auth.logout', 'static', 'main.health_check']
        if request.endpoint in skip_routes or request.endpoint is None:
            return
        
        # Skip validation for non-authenticated users
        if not current_user.is_authenticated:
            return
        
        # Get session token
        session_token = session.get('session_token')
        if not session_token:
            # No session token, force logout
            logout_user()
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Validate session and check timeout
        user_session, status = UserSession.validate_session(session_token, max_idle_minutes=15)
        
        if not user_session:
            # Session invalid or expired
            if "expired" in status.lower():
                # Log the timeout
                UserActivity.log_activity(
                    user_id=current_user.id,
                    activity_type='timeout_logout',
                    session_token=session_token,
                    details={'reason': status},
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            
            # Force logout
            logout_user()
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Session is valid, session activity already updated in validate_session()
    
    # Cleanup expired sessions periodically
    @app.before_request
    def cleanup_sessions():
        """Cleanup expired sessions (run randomly to avoid overhead)"""
        import random
        from .models import UserSession
        
        # Only run cleanup 1% of the time to avoid overhead
        if random.random() < 0.01:
            try:
                expired_count = UserSession.cleanup_expired_sessions()
                if expired_count > 0:
                    print(f"Cleaned up {expired_count} expired sessions")
            except Exception as e:
                print(f"Session cleanup error: {e}")
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    
    # Register main routes
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app