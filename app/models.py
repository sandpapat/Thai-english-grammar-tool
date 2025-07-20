from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func, Enum
import enum

db = SQLAlchemy()

class UserType(enum.Enum):
    """User type enumeration"""
    NORMAL = 'normal'
    PROFICIENT = 'proficient'

class Pseudocode(UserMixin, db.Model):
    """Anonymous user model using only 5-digit pseudocodes"""
    __tablename__ = 'pseudocodes'
    
    id = db.Column(db.Integer, primary_key=True)
    pseudocode = db.Column(db.String(5), unique=True, nullable=False, index=True)
    user_type = db.Column(Enum(UserType), default=UserType.NORMAL, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=None)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Pseudocode {self.pseudocode} ({self.user_type.value})>'
    
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
            return self.user_type.value.capitalize()
        except AttributeError:
            # Fallback for when user_type column doesn't exist yet
            return "Proficient" if self.is_proficient() else "Normal"
    
    def get_id(self):
        """Required for Flask-Login"""
        return str(self.id)
    
    @staticmethod
    def verify_pseudocode(pseudocode):
        """Verify if a pseudocode exists and is active"""
        if not pseudocode or len(pseudocode) != 5 or not pseudocode.isdigit():
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
        if len(pseudocode) != 5 or not pseudocode.isdigit():
            raise ValueError("Pseudocode must be exactly 5 digits")
        
        # Check if already exists
        existing = Pseudocode.query.filter_by(pseudocode=pseudocode).first()
        if existing:
            raise ValueError("Pseudocode already exists")
        
        # Auto-determine user type based on pseudocode range (for demo purposes)
        # Proficient users: pseudocodes starting with 9 (90000-99999)
        if pseudocode.startswith('9'):
            user_type = UserType.PROFICIENT
        
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
    """User rating model for proficient users to rate translation and overall quality"""
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('pseudocodes.id'), nullable=False, index=True)
    input_thai = db.Column(db.Text, nullable=False)  # Original Thai text
    translation_text = db.Column(db.Text, nullable=False)  # Translation that was rated
    translation_rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    overall_quality_rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    comments = db.Column(db.Text, nullable=True)  # Optional user comments
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = db.relationship('Pseudocode', backref=db.backref('ratings', lazy=True))
    
    def __repr__(self):
        return f'<Rating {self.id}: T:{self.translation_rating}/5 O:{self.overall_quality_rating}/5>'
    
    @staticmethod
    def create_rating(user_id, input_thai, translation_text, translation_rating, overall_quality_rating, comments=None):
        """Create a new rating entry"""
        # Validate ratings are in 1-5 range
        if not (1 <= translation_rating <= 5) or not (1 <= overall_quality_rating <= 5):
            raise ValueError("Ratings must be between 1 and 5")
        
        # Verify user is proficient
        user = Pseudocode.query.get(user_id)
        if not user or not user.is_proficient():
            raise ValueError("Only proficient users can submit ratings")
        
        rating = Rating(
            user_id=user_id,
            input_thai=input_thai,
            translation_text=translation_text,
            translation_rating=translation_rating,
            overall_quality_rating=overall_quality_rating,
            comments=comments
        )
        
        db.session.add(rating)
        db.session.commit()
        return rating
    
    @staticmethod
    def get_rating_stats():
        """Get aggregate rating statistics"""
        total_ratings = Rating.query.count()
        
        if total_ratings == 0:
            return {
                'total_ratings': 0,
                'avg_translation_rating': 0,
                'avg_overall_rating': 0,
                'rating_distribution': {}
            }
        
        # Average ratings
        avg_stats = db.session.query(
            func.avg(Rating.translation_rating).label('avg_translation'),
            func.avg(Rating.overall_quality_rating).label('avg_overall')
        ).first()
        
        # Rating distribution
        translation_dist = db.session.query(
            Rating.translation_rating,
            func.count(Rating.translation_rating)
        ).group_by(Rating.translation_rating).all()
        
        overall_dist = db.session.query(
            Rating.overall_quality_rating,
            func.count(Rating.overall_quality_rating)
        ).group_by(Rating.overall_quality_rating).all()
        
        return {
            'total_ratings': total_ratings,
            'avg_translation_rating': round(avg_stats.avg_translation or 0, 2),
            'avg_overall_rating': round(avg_stats.avg_overall or 0, 2),
            'translation_distribution': {str(rating): count for rating, count in translation_dist},
            'overall_distribution': {str(rating): count for rating, count in overall_dist}
        }