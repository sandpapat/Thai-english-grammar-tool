from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import func
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class UserType:
    """User type constants"""
    NORMAL = 'normal'
    PROFICIENT = 'proficient'
    
    @classmethod
    def is_valid(cls, value):
        """Check if a user type value is valid"""
        return value in [cls.NORMAL, cls.PROFICIENT]

class Pseudocode(UserMixin, db.Model):
    """Anonymous user model using 5-character pseudocodes"""
    __tablename__ = 'pseudocodes'
    
    id = db.Column(db.Integer, primary_key=True)
    pseudocode = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_type = db.Column(db.String(20), default=UserType.NORMAL, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=None)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Pseudocode {self.pseudocode} ({self.user_type})>'
    
    def is_proficient(self):
        """Check if user is proficient type"""
        try:
            return self.user_type == UserType.PROFICIENT
        except AttributeError:
            # Fallback for when user_type column doesn't exist yet
            return self.pseudocode.startswith('9') if hasattr(self, 'pseudocode') else False
    
    def get_user_type_display(self):
        """Get user type for display purposes"""
        try:
            return self.user_type.capitalize()
        except AttributeError:
            # Fallback for when user_type column doesn't exist yet
            return "Proficient" if self.is_proficient() else "Normal"
    
    def set_user_type(self, user_type):
        """Set user type with validation"""
        if not UserType.is_valid(user_type):
            raise ValueError(f"Invalid user type: {user_type}. Must be one of: {UserType.NORMAL}, {UserType.PROFICIENT}")
        self.user_type = user_type
    
    def get_id(self):
        """Required for Flask-Login"""
        return str(self.id)
    
    @staticmethod
    def verify_pseudocode(pseudocode):
        """Verify if a pseudocode exists and is active"""
        if not pseudocode or len(pseudocode) != 5 or not pseudocode.isalnum():
            return None
        
        user = Pseudocode.query.filter_by(pseudocode=pseudocode, is_active=True).first()
        if user:
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
        return user
    
    @staticmethod
    def create_pseudocode(pseudocode, user_type=UserType.NORMAL):
        """Create a new pseudocode entry"""
        # Validate pseudocode format - exactly 5 characters, letters and numbers only
        if len(pseudocode) != 5:
            raise ValueError("Pseudocode must be exactly 5 characters")
        
        if not pseudocode.isalnum():
            raise ValueError("Pseudocode can only contain letters and numbers")
        
        # Validate user type
        if not UserType.is_valid(user_type):
            raise ValueError(f"Invalid user type: {user_type}")
        
        # Check if already exists
        existing = Pseudocode.query.filter_by(pseudocode=pseudocode).first()
        if existing:
            raise ValueError("Pseudocode already exists")
        
        new_user = Pseudocode(pseudocode=pseudocode, user_type=user_type)
        db.session.add(new_user)
        db.session.commit()
        return new_user


class SystemPerformance(db.Model):
    """Privacy-compliant performance tracking model"""
    __tablename__ = 'system_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('pseudocodes.id'), nullable=True, index=True)
    input_length = db.Column(db.Integer, nullable=False)
    translation_time = db.Column(db.Float, nullable=True)
    classification_time = db.Column(db.Float, nullable=True)
    explanation_time = db.Column(db.Float, nullable=True)
    total_time = db.Column(db.Float, nullable=False)
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_stage = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = db.relationship('Pseudocode', backref=db.backref('performance_logs', lazy=True))
    
    def __repr__(self):
        return f'<SystemPerformance {self.id}: {self.total_time}s>'
    
    @staticmethod
    def log_performance(user_id, input_length, translation_time=None, classification_time=None, 
                       explanation_time=None, success=True, error_stage=None):
        """Log a performance entry"""
        total_time = 0.0
        if translation_time:
            total_time += translation_time
        if classification_time:
            total_time += classification_time
        if explanation_time:
            total_time += explanation_time
            
        performance = SystemPerformance(
            user_id=user_id,
            input_length=input_length,
            translation_time=translation_time,
            classification_time=classification_time,
            explanation_time=explanation_time,
            total_time=total_time,
            success=success,
            error_stage=error_stage
        )
        
        db.session.add(performance)
        db.session.commit()
        return performance
    
    @staticmethod
    def get_performance_stats():
        """Get aggregate performance statistics"""
        # Total usage stats
        total_requests = SystemPerformance.query.count()
        successful_requests = SystemPerformance.query.filter_by(success=True).count()
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Average timing stats for successful requests
        successful_logs = SystemPerformance.query.filter_by(success=True)
        
        avg_stats = db.session.query(
            func.avg(SystemPerformance.translation_time).label('avg_translation'),
            func.avg(SystemPerformance.classification_time).label('avg_classification'),
            func.avg(SystemPerformance.explanation_time).label('avg_explanation'),
            func.avg(SystemPerformance.total_time).label('avg_total'),
            func.avg(SystemPerformance.input_length).label('avg_input_length')
        ).filter_by(success=True).first()
        
        # Recent performance (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_requests = SystemPerformance.query.filter(
            SystemPerformance.timestamp >= yesterday
        ).count()
        
        # Unique users
        unique_users = db.session.query(SystemPerformance.user_id).distinct().count()
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': round(success_rate, 1),
            'avg_translation_time': round(avg_stats.avg_translation or 0, 3),
            'avg_classification_time': round(avg_stats.avg_classification or 0, 3),
            'avg_explanation_time': round(avg_stats.avg_explanation or 0, 3),
            'avg_total_time': round(avg_stats.avg_total or 0, 3),
            'avg_input_length': round(avg_stats.avg_input_length or 0, 1),
            'recent_requests_24h': recent_requests,
            'unique_users': unique_users
        }


class Rating(db.Model):
    """Enhanced rating model for proficient users with multi-criteria assessment"""
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('pseudocodes.id'), nullable=False, index=True)
    input_thai = db.Column(db.Text, nullable=False)  # Original Thai text
    translation_text = db.Column(db.Text, nullable=False)  # Translation that was rated
    
    # Multi-criteria ratings (1-5 scale)
    translation_accuracy = db.Column(db.Integer, nullable=False)  # Does English correctly convey Thai meaning?
    translation_fluency = db.Column(db.Integer, nullable=False)  # Does English sound natural?
    explanation_quality = db.Column(db.Integer, nullable=False)  # Is grammar explanation accurate and helpful?
    educational_value = db.Column(db.Integer, nullable=False)  # How helpful for Thai English learners?
    
    # Legacy fields for backward compatibility (will be migrated)
    translation_rating = db.Column(db.Integer, nullable=True)  # Legacy field - to be removed after migration
    overall_quality_rating = db.Column(db.Integer, nullable=True)  # To be removed
    
    # Additional feedback
    issue_tags = db.Column(db.JSON, nullable=True)  # Array of selected issue tags
    comments = db.Column(db.Text, nullable=True)  # Optional user comments
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = db.relationship('Pseudocode', backref=db.backref('ratings', lazy=True))
    
    def __repr__(self):
        return f'<Rating {self.id}: Acc:{self.translation_accuracy}/5 Flu:{self.translation_fluency}/5 Exp:{self.explanation_quality}/5 Edu:{self.educational_value}/5>'
    
    @staticmethod
    def create_rating(user_id, input_thai, translation_text, translation_accuracy, translation_fluency, 
                     explanation_quality, educational_value, issue_tags=None, comments=None):
        """Create a new rating entry with multi-criteria assessment"""
        # Validate all ratings are in 1-5 range
        ratings = {
            'translation_accuracy': translation_accuracy,
            'translation_fluency': translation_fluency,
            'explanation_quality': explanation_quality,
            'educational_value': educational_value
        }
        
        for field, value in ratings.items():
            if not isinstance(value, int) or not (1 <= value <= 5):
                raise ValueError(f"{field} must be an integer between 1 and 5")
        
        # Verify user is proficient
        user = Pseudocode.query.get(user_id)
        if not user or not user.is_proficient():
            raise ValueError("Only proficient users can submit ratings")
        
        rating = Rating(
            user_id=user_id,
            input_thai=input_thai,
            translation_text=translation_text,
            translation_accuracy=translation_accuracy,
            translation_fluency=translation_fluency,
            explanation_quality=explanation_quality,
            educational_value=educational_value,
            issue_tags=issue_tags,
            comments=comments,
            # Set legacy fields to maintain backward compatibility
            translation_rating=translation_accuracy,  # Use accuracy as legacy translation rating
            overall_quality_rating=educational_value  # Use educational value as legacy overall rating
        )
        
        db.session.add(rating)
        db.session.commit()
        return rating
    
    @staticmethod
    def get_rating_stats():
        """Get aggregate rating statistics for enhanced multi-criteria ratings"""
        total_ratings = Rating.query.count()
        
        if total_ratings == 0:
            return {
                'total_ratings': 0,
                'avg_translation_accuracy': 0,
                'avg_translation_fluency': 0,
                'avg_explanation_quality': 0,
                'avg_educational_value': 0,
                'rating_distributions': {},
                'common_issue_tags': []
            }
        
        # Average ratings for all criteria
        avg_stats = db.session.query(
            func.avg(Rating.translation_accuracy).label('avg_accuracy'),
            func.avg(Rating.translation_fluency).label('avg_fluency'),
            func.avg(Rating.explanation_quality).label('avg_explanation'),
            func.avg(Rating.educational_value).label('avg_educational')
        ).first()
        
        # Get distribution for each criterion
        distributions = {}
        for criterion in ['translation_accuracy', 'translation_fluency', 'explanation_quality', 'educational_value']:
            dist = db.session.query(
                getattr(Rating, criterion),
                func.count(getattr(Rating, criterion))
            ).group_by(getattr(Rating, criterion)).all()
            distributions[criterion] = {str(rating): count for rating, count in dist}
        
        # Get common issue tags
        all_tags = []
        ratings_with_tags = Rating.query.filter(Rating.issue_tags.isnot(None)).all()
        for rating in ratings_with_tags:
            if rating.issue_tags:
                all_tags.extend(rating.issue_tags)
        
        # Count tag frequency
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort tags by frequency
        common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_ratings': total_ratings,
            'avg_translation_accuracy': round(avg_stats.avg_accuracy or 0, 2),
            'avg_translation_fluency': round(avg_stats.avg_fluency or 0, 2),
            'avg_explanation_quality': round(avg_stats.avg_explanation or 0, 2),
            'avg_educational_value': round(avg_stats.avg_educational or 0, 2),
            'rating_distributions': distributions,
            'common_issue_tags': common_tags
        }


class UserSession(db.Model):
    """Single-device session management for users"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('pseudocodes.id'), nullable=False)
    session_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # IPv6 support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationship
    user = db.relationship('Pseudocode', backref=db.backref('sessions', lazy=True))
    
    def __repr__(self):
        return f'<UserSession {self.user_id}: {self.session_token[:8]}... (active: {self.is_active})>'
    
    @staticmethod
    def create_session(user_id, user_agent=None, ip_address=None):
        """Create new session and deactivate any existing sessions for this user"""
        # First, deactivate all existing sessions for this user (single-device login)
        UserSession.query.filter_by(user_id=user_id, is_active=True).update({
            'is_active': False,
            'last_activity': datetime.utcnow()
        })
        
        # Create new session
        session = UserSession(
            user_id=user_id,
            session_token=str(uuid.uuid4()),
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        db.session.add(session)
        db.session.commit()
        return session
    
    @staticmethod
    def get_active_session(user_id):
        """Get the active session for a user"""
        return UserSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).first()
    
    @staticmethod
    def validate_session(session_token, max_idle_minutes=15):
        """Validate session and check for idle timeout"""
        session = UserSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()
        
        if not session:
            return None, "Session not found or inactive"
        
        # Check idle timeout
        idle_time = datetime.utcnow() - session.last_activity
        if idle_time > timedelta(minutes=max_idle_minutes):
            # Session expired due to inactivity
            session.is_active = False
            db.session.commit()
            return None, f"Session expired after {max_idle_minutes} minutes of inactivity"
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        db.session.commit()
        
        return session, "Valid"
    
    @staticmethod
    def cleanup_expired_sessions(max_idle_minutes=15):
        """Clean up expired sessions (call this periodically)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_idle_minutes)
        
        expired_count = UserSession.query.filter(
            UserSession.is_active == True,
            UserSession.last_activity < cutoff_time
        ).update({
            'is_active': False,
            'last_activity': datetime.utcnow()
        })
        
        db.session.commit()
        return expired_count
    
    def invalidate(self):
        """Invalidate this session"""
        self.is_active = False
        self.last_activity = datetime.utcnow()
        db.session.commit()


class UserActivity(db.Model):
    """User activity tracking for analytics"""
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('pseudocodes.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False, index=True)  # 'login', 'translation', 'feedback', 'logout'
    session_token = db.Column(db.String(64), index=True)
    details = db.Column(db.JSON)  # Store additional activity details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Relationship
    user = db.relationship('Pseudocode', backref=db.backref('activities', lazy=True))
    
    def __repr__(self):
        return f'<UserActivity {self.user_id}: {self.activity_type} at {self.timestamp}>'
    
    @staticmethod
    def log_activity(user_id, activity_type, session_token=None, details=None, ip_address=None, user_agent=None):
        """Log user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            session_token=session_token,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(activity)
        db.session.commit()
        return activity
    
    @staticmethod
    def get_user_stats(user_id, days=30):
        """Get user activity statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total activities
        total_activities = UserActivity.query.filter(
            UserActivity.user_id == user_id,
            UserActivity.timestamp >= cutoff_date
        ).count()
        
        # Activity breakdown
        activity_counts = db.session.query(
            UserActivity.activity_type,
            func.count(UserActivity.id)
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.timestamp >= cutoff_date
        ).group_by(UserActivity.activity_type).all()
        
        # Daily activity counts for chart
        daily_activity = db.session.query(
            func.date(UserActivity.timestamp).label('date'),
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.timestamp >= cutoff_date
        ).group_by(func.date(UserActivity.timestamp)).all()
        
        # Translation specific stats
        translation_count = UserActivity.query.filter(
            UserActivity.user_id == user_id,
            UserActivity.activity_type == 'translation',
            UserActivity.timestamp >= cutoff_date
        ).count()
        
        # Feedback stats (for proficient users)
        feedback_count = UserActivity.query.filter(
            UserActivity.user_id == user_id,
            UserActivity.activity_type == 'feedback',
            UserActivity.timestamp >= cutoff_date
        ).count()
        
        # Login frequency
        login_count = UserActivity.query.filter(
            UserActivity.user_id == user_id,
            UserActivity.activity_type == 'login',
            UserActivity.timestamp >= cutoff_date
        ).count()
        
        # Last activity
        last_activity = UserActivity.query.filter(
            UserActivity.user_id == user_id
        ).order_by(UserActivity.timestamp.desc()).first()
        
        return {
            'total_activities': total_activities,
            'activity_breakdown': {activity_type: count for activity_type, count in activity_counts},
            'daily_activity': [
                {'date': str(date), 'count': count} 
                for date, count in daily_activity
            ],
            'translation_count': translation_count,
            'feedback_count': feedback_count,
            'login_count': login_count,
            'last_activity': last_activity.timestamp if last_activity else None,
            'days_analyzed': days
        }
    
    @staticmethod
    def get_all_user_summary():
        """Get summary statistics for all users"""
        # Most active users
        most_active = db.session.query(
            UserActivity.user_id,
            func.count(UserActivity.id).label('activity_count')
        ).group_by(UserActivity.user_id).order_by(
            func.count(UserActivity.id).desc()
        ).limit(10).all()
        
        # Activity type distribution
        activity_dist = db.session.query(
            UserActivity.activity_type,
            func.count(UserActivity.id)
        ).group_by(UserActivity.activity_type).all()
        
        return {
            'most_active_users': [
                {'user_id': user_id, 'activity_count': count} 
                for user_id, count in most_active
            ],
            'activity_distribution': {
                activity_type: count for activity_type, count in activity_dist
            }
        }


class Admin(UserMixin, db.Model):
    """Admin user model for dashboard access"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Activity logging
    activities = db.relationship('AdminActivity', backref='admin', lazy='dynamic')
    
    def __repr__(self):
        return f'<Admin {self.username}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Required for Flask-Login"""
        return f"admin-{self.id}"
    
    @staticmethod
    def create_admin(username, email, password, full_name=None, is_super_admin=False):
        """Create a new admin user"""
        # Check if admin already exists
        existing = Admin.query.filter(
            (Admin.username == username) | (Admin.email == email)
        ).first()
        if existing:
            raise ValueError("Admin with this username or email already exists")
        
        admin = Admin(
            username=username,
            email=email,
            full_name=full_name,
            is_super_admin=is_super_admin
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        return admin
    
    def log_activity(self, activity_type, details=None):
        """Log admin activity"""
        activity = AdminActivity(
            admin_id=self.id,
            activity_type=activity_type,
            details=details
        )
        db.session.add(activity)
        db.session.commit()


class AdminActivity(db.Model):
    """Admin activity logging"""
    __tablename__ = 'admin_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # login, user_add, user_edit, data_export, etc.
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    
    def __repr__(self):
        return f'<AdminActivity {self.admin_id}: {self.activity_type} at {self.timestamp}>'