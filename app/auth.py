from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Pseudocode, UserSession, UserActivity, db
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - only requires 5-digit pseudocode"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        pseudocode = request.form.get('pseudocode', '').strip()
        
        # Basic validation
        if not pseudocode:
            flash('Please enter your 5-character code', 'error')
            return render_template('login.html')
        
        if len(pseudocode) != 5 or not pseudocode.isalnum():
            flash('Invalid code format. Please enter exactly 5 characters (letters and numbers)', 'error')
            return render_template('login.html')
        
        # Verify pseudocode
        user = Pseudocode.verify_pseudocode(pseudocode)
        
        if user:
            # Check for existing active sessions (single-device login)
            existing_session = UserSession.get_active_session(user.id)
            if existing_session:
                flash('Your account is already logged in from another device. Logging out other sessions.', 'warning')
                # Log activity for the forced logout
                UserActivity.log_activity(
                    user_id=user.id,
                    activity_type='forced_logout',
                    details={'reason': 'single_device_login', 'old_session': existing_session.session_token[:8]},
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            
            # Create new session (this will automatically deactivate existing ones)
            user_session = UserSession.create_session(
                user_id=user.id,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            # Store session token in Flask session
            session['session_token'] = user_session.session_token
            
            # Log the user in with Flask-Login
            login_user(user, remember=False)  # Don't remember - use our session management
            
            # Log the login activity
            UserActivity.log_activity(
                user_id=user.id,
                activity_type='login',
                session_token=user_session.session_token,
                details={'login_method': 'pseudocode'},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            flash('Successfully logged in!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid code. Please check your 5-character code and try again', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    # Log the logout activity before logging out
    if current_user.is_authenticated:
        session_token = session.get('session_token')
        UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='logout',
            session_token=session_token,
            details={'logout_method': 'manual'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Invalidate the session
        if session_token:
            user_session = UserSession.query.filter_by(
                session_token=session_token,
                is_active=True
            ).first()
            if user_session:
                user_session.invalidate()
    
    # Clear Flask session
    session.pop('session_token', None)
    
    # Flask-Login logout
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))