"""
Admin dashboard routes and functionality
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user, login_user, logout_user
from functools import wraps
from datetime import datetime, timedelta
import csv
import io
from sqlalchemy import desc, func
from .models import db, Admin, AdminActivity, Pseudocode, UserType, Rating, SystemPerformance, UserSession, UserActivity

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check if current user is an admin
        if not hasattr(current_user, 'is_super_admin'):
            flash('Admin access required', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if current_user.is_authenticated and hasattr(current_user, 'is_super_admin'):
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('admin/admin_login.html')
        
        # Find admin user
        admin = Admin.query.filter_by(username=username, is_active=True).first()
        
        if admin and admin.check_password(password):
            # Log the user in
            login_user(admin, remember=True)
            
            # Update last login
            admin.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            admin.log_activity('login', {
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            })
            
            flash('Welcome to the admin dashboard!', 'success')
            
            # Redirect to requested page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/admin'):
                return redirect(next_page)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin/admin_login.html')


@admin_bp.route('/logout')
@admin_required
def logout():
    """Admin logout"""
    if hasattr(current_user, 'log_activity'):
        current_user.log_activity('logout')
    
    logout_user()
    flash('You have been logged out from admin panel', 'info')
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    """Main admin dashboard"""
    # Get overview statistics
    stats = {
        'total_users': Pseudocode.query.count(),
        'active_users': Pseudocode.query.filter_by(is_active=True).count(),
        'proficient_users': Pseudocode.query.filter_by(user_type=UserType.PROFICIENT).count(),
        'total_ratings': Rating.query.count(),
        'online_users': UserSession.query.filter_by(is_active=True).count(),
        'total_translations': UserActivity.query.filter_by(activity_type='translation').count()
    }
    
    # Get recent activities
    recent_activities = UserActivity.query.order_by(desc(UserActivity.timestamp)).limit(10).all()
    
    # Get top users by activity
    top_users = db.session.query(
        UserActivity.user_id,
        Pseudocode.pseudocode,
        func.count(UserActivity.id).label('activity_count')
    ).join(Pseudocode).filter(
        UserActivity.activity_type == 'translation'
    ).group_by(UserActivity.user_id, Pseudocode.pseudocode).order_by(
        desc('activity_count')
    ).limit(5).all()
    
    # Get rating statistics
    rating_stats = Rating.get_rating_stats()
    
    return render_template('admin/admin_dashboard.html', 
                         stats=stats, 
                         recent_activities=recent_activities,
                         top_users=top_users,
                         rating_stats=rating_stats)


@admin_bp.route('/users')
@admin_required
def users():
    """User management page"""
    # Get filter parameters
    user_type = request.args.get('type', 'all')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Pseudocode.query
    
    if user_type != 'all':
        query = query.filter_by(user_type=user_type)
    
    if search:
        query = query.filter(Pseudocode.pseudocode.contains(search))
    
    # Paginate results
    pagination = query.order_by(desc(Pseudocode.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    users = pagination.items
    
    # Add activity counts for each user
    for user in users:
        user.translation_count = UserActivity.query.filter_by(
            user_id=user.id, 
            activity_type='translation'
        ).count()
        user.rating_count = Rating.query.filter_by(user_id=user.id).count()
    
    return render_template('admin/admin_users.html', 
                         users=users, 
                         pagination=pagination,
                         user_type=user_type,
                         search=search)


@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Add a new user"""
    try:
        pseudocode = request.form.get('pseudocode', '').strip().upper()
        user_type = request.form.get('user_type', UserType.NORMAL)
        
        # Create the user
        user = Pseudocode.create_pseudocode(pseudocode, user_type)
        
        # Log admin activity
        current_user.log_activity('user_add', {
            'pseudocode': pseudocode,
            'user_type': user_type
        })
        
        flash(f'User {pseudocode} added successfully', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash('Error adding user', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-type', methods=['POST'])
@admin_required
def toggle_user_type(user_id):
    """Toggle user type between Normal and Proficient"""
    try:
        user = Pseudocode.query.get_or_404(user_id)
        old_type = user.user_type
        
        # Toggle type
        new_type = UserType.PROFICIENT if user.user_type == UserType.NORMAL else UserType.NORMAL
        user.set_user_type(new_type)
        
        db.session.commit()
        
        # Log admin activity
        current_user.log_activity('user_type_change', {
            'user_id': user_id,
            'pseudocode': user.pseudocode,
            'old_type': old_type,
            'new_type': new_type
        })
        
        flash(f'User {user.pseudocode} type changed to {new_type}', 'success')
    except Exception as e:
        flash('Error updating user type', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    try:
        user = Pseudocode.query.get_or_404(user_id)
        user.is_active = not user.is_active
        
        db.session.commit()
        
        # Log admin activity
        current_user.log_activity('user_toggle_active', {
            'user_id': user_id,
            'pseudocode': user.pseudocode,
            'is_active': user.is_active
        })
        
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.pseudocode} {status}', 'success')
    except Exception as e:
        flash('Error updating user status', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/ratings')
@admin_required
def ratings():
    """View all ratings"""
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    user_filter = request.args.get('user', '')
    min_rating = request.args.get('min_rating', 0, type=int)
    
    # Build query
    query = Rating.query.join(Pseudocode)
    
    if user_filter:
        query = query.filter(Pseudocode.pseudocode.contains(user_filter))
    
    if min_rating > 0:
        query = query.filter(
            (Rating.translation_accuracy >= min_rating) |
            (Rating.educational_value >= min_rating)
        )
    
    # Paginate results
    pagination = query.order_by(desc(Rating.timestamp)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    ratings = pagination.items
    
    return render_template('admin/admin_ratings.html', 
                         ratings=ratings,
                         pagination=pagination,
                         user_filter=user_filter,
                         min_rating=min_rating)


@admin_bp.route('/exports')
@admin_required
def exports():
    """Data export page"""
    return render_template('admin/admin_exports.html')


@admin_bp.route('/export/ratings')
@admin_required
def export_ratings():
    """Export ratings to CSV"""
    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Timestamp', 'User', 'User Type', 'Thai Input', 'English Translation',
            'Translation Accuracy', 'Translation Fluency', 'Explanation Quality', 
            'Educational Value', 'Issue Tags', 'Comments'
        ])
        
        # Get all ratings
        ratings = Rating.query.join(Pseudocode).order_by(desc(Rating.timestamp)).all()
        
        for rating in ratings:
            writer.writerow([
                rating.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                rating.user.pseudocode,
                rating.user.user_type,
                rating.input_thai,
                rating.translation_text,
                rating.translation_accuracy,
                rating.translation_fluency,
                rating.explanation_quality,
                rating.educational_value,
                ', '.join(rating.issue_tags) if rating.issue_tags else '',
                rating.comments or ''
            ])
        
        # Create response
        output.seek(0)
        
        # Log activity
        current_user.log_activity('export_ratings', {
            'count': len(ratings)
        })
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash('Error exporting ratings', 'error')
        return redirect(url_for('admin.exports'))


@admin_bp.route('/export/users')
@admin_required
def export_users():
    """Export users to CSV"""
    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Pseudocode', 'User Type', 'Created At', 'Last Login', 'Active',
            'Translation Count', 'Rating Count'
        ])
        
        # Get all users with activity counts
        users = Pseudocode.query.all()
        
        for user in users:
            translation_count = UserActivity.query.filter_by(
                user_id=user.id, 
                activity_type='translation'
            ).count()
            rating_count = Rating.query.filter_by(user_id=user.id).count()
            
            writer.writerow([
                user.pseudocode,
                user.user_type,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                'Yes' if user.is_active else 'No',
                translation_count,
                rating_count
            ])
        
        # Create response
        output.seek(0)
        
        # Log activity
        current_user.log_activity('export_users', {
            'count': len(users)
        })
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash('Error exporting users', 'error')
        return redirect(url_for('admin.exports'))


@admin_bp.route('/export/activity')
@admin_required
def export_activity():
    """Export user activity to CSV"""
    try:
        # Get date range from request
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Timestamp', 'User', 'Activity Type', 'Details', 'IP Address'
        ])
        
        # Get activities
        activities = UserActivity.query.join(Pseudocode).filter(
            UserActivity.timestamp >= cutoff_date
        ).order_by(desc(UserActivity.timestamp)).all()
        
        for activity in activities:
            writer.writerow([
                activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                activity.user.pseudocode,
                activity.activity_type,
                str(activity.details) if activity.details else '',
                activity.ip_address or ''
            ])
        
        # Create response
        output.seek(0)
        
        # Log activity
        current_user.log_activity('export_activity', {
            'days': days,
            'count': len(activities)
        })
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'activity_export_{days}days_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        flash('Error exporting activity', 'error')
        return redirect(url_for('admin.exports'))


@admin_bp.route('/api/online-users')
@admin_required
def get_online_users():
    """API endpoint to get currently online users"""
    try:
        # Get active sessions with user details
        active_sessions = db.session.query(
            UserSession, Pseudocode
        ).join(Pseudocode).filter(
            UserSession.is_active == True
        ).order_by(desc(UserSession.last_activity)).all()
        
        online_users = []
        for session, user in active_sessions:
            # Calculate session duration
            duration = datetime.utcnow() - session.created_at
            
            online_users.append({
                'pseudocode': user.pseudocode,
                'user_type': user.user_type,
                'session_start': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'duration_minutes': int(duration.total_seconds() / 60),
                'ip_address': session.ip_address
            })
        
        return jsonify({
            'success': True,
            'online_count': len(online_users),
            'users': online_users
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/dashboard-stats')
@admin_required
def get_dashboard_stats():
    """API endpoint for real-time dashboard statistics"""
    try:
        # Get various statistics
        stats = {
            'users': {
                'total': Pseudocode.query.count(),
                'active': Pseudocode.query.filter_by(is_active=True).count(),
                'proficient': Pseudocode.query.filter_by(user_type=UserType.PROFICIENT).count(),
                'online': UserSession.query.filter_by(is_active=True).count()
            },
            'activity': {
                'translations_today': UserActivity.query.filter(
                    UserActivity.activity_type == 'translation',
                    UserActivity.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0)
                ).count(),
                'ratings_today': Rating.query.filter(
                    Rating.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0)
                ).count()
            },
            'performance': SystemPerformance.get_performance_stats()
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Initialize admin user if needed (run this once)
def init_admin():
    """Initialize default admin user if none exists"""
    if Admin.query.count() == 0:
        try:
            admin = Admin.create_admin(
                username='admin',
                email='admin@thaislate.com',
                password='changeme123',  # CHANGE THIS IN PRODUCTION
                full_name='System Administrator',
                is_super_admin=True
            )
            print(f"Created default admin user: {admin.username}")
            print("IMPORTANT: Change the default password immediately!")
        except Exception as e:
            print(f"Error creating admin user: {e}")