"""
Flask application factory and configuration
"""
import os
from flask import Flask
from flask_login import LoginManager
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
    elif config_name == 'production':
        app.config['DEBUG'] = False
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    else:
        app.config['DEBUG'] = True
    
    # Model configuration
    app.config['MAX_TOKENS'] = 500
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
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    
    # Register main routes
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app