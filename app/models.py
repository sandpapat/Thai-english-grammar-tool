from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Pseudocode(UserMixin, db.Model):
    """Anonymous user model using only 5-digit pseudocodes"""
    __tablename__ = 'pseudocodes'
    
    id = db.Column(db.Integer, primary_key=True)
    pseudocode = db.Column(db.String(5), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=None)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Pseudocode {self.pseudocode}>'
    
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
    def create_pseudocode(pseudocode):
        """Create a new pseudocode entry"""
        if len(pseudocode) != 5 or not pseudocode.isdigit():
            raise ValueError("Pseudocode must be exactly 5 digits")
        
        # Check if already exists
        existing = Pseudocode.query.filter_by(pseudocode=pseudocode).first()
        if existing:
            raise ValueError("Pseudocode already exists")
        
        new_user = Pseudocode(pseudocode=pseudocode)
        db.session.add(new_user)
        db.session.commit()
        return new_user