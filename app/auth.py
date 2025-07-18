from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Pseudocode, db
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
            flash('Please enter your 5-digit code', 'error')
            return render_template('login.html')
        
        if len(pseudocode) != 5 or not pseudocode.isdigit():
            flash('Invalid code format. Please enter exactly 5 digits', 'error')
            return render_template('login.html')
        
        # Verify pseudocode
        user = Pseudocode.verify_pseudocode(pseudocode)
        
        if user:
            # Log the user in
            login_user(user, remember=True, duration=timedelta(hours=24))
            flash('Successfully logged in!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid code. Please check your 5-digit code and try again', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))