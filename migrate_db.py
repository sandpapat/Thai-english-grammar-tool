#!/usr/bin/env python3
"""
Database migration script for user type system
This script adds the user_type column and creates the Rating table
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Pseudocode, UserType, Rating

def migrate_database():
    """Migrate database to add user types and ratings"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting database migration...")
        
        try:
            # Create all tables (this will create new ones and skip existing ones)
            db.create_all()
            print("✅ Database tables created/updated successfully")
            
            # Check if user_type column exists in existing pseudocodes
            # This is a simple check - in production you'd use proper migrations
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pseudocodes')]
            
            if 'user_type' not in columns:
                print("⚠️  Warning: user_type column may not exist in existing pseudocodes table")
                print("   Manual database migration may be required")
            else:
                print("✅ user_type column exists in pseudocodes table")
                
                # Update existing users to have normal type if they don't have one
                users_without_type = Pseudocode.query.filter(Pseudocode.user_type.is_(None)).all()
                for user in users_without_type:
                    user.user_type = UserType.NORMAL
                
                if users_without_type:
                    db.session.commit()
                    print(f"✅ Updated {len(users_without_type)} existing users to Normal type")
            
            # Create some sample proficient users for testing
            sample_proficient_codes = ['90001', '90002', '91000', '92000', '99999']
            created_count = 0
            
            for code in sample_proficient_codes:
                existing = Pseudocode.query.filter_by(pseudocode=code).first()
                if not existing:
                    try:
                        new_user = Pseudocode.create_pseudocode(code, UserType.PROFICIENT)
                        created_count += 1
                        print(f"✅ Created proficient user: {code}")
                    except ValueError as e:
                        print(f"⚠️  Skipped {code}: {e}")
                else:
                    # Update existing user to proficient if it's in our sample range
                    if existing.user_type != UserType.PROFICIENT:
                        existing.user_type = UserType.PROFICIENT
                        created_count += 1
                        print(f"✅ Updated {code} to proficient user")
            
            if created_count > 0:
                db.session.commit()
                print(f"✅ Created/updated {created_count} proficient users")
            
            # Display current user counts
            total_users = Pseudocode.query.count()
            normal_users = Pseudocode.query.filter_by(user_type=UserType.NORMAL).count()
            proficient_users = Pseudocode.query.filter_by(user_type=UserType.PROFICIENT).count()
            
            print(f"\n📊 Current user statistics:")
            print(f"   Total users: {total_users}")
            print(f"   Normal users: {normal_users}")
            print(f"   Proficient users: {proficient_users}")
            
            # Check ratings table
            rating_count = Rating.query.count()
            print(f"   Total ratings: {rating_count}")
            
            print("\n🎉 Database migration completed successfully!")
            print("\n📋 Test Instructions:")
            print("   1. Log in with a normal user (00001-89999)")
            print("   2. Normal users should see 'Normal' badge in navigation")
            print("   3. Log in with a proficient user (90001, 90002, 91000, 92000, 99999)")
            print("   4. Proficient users should see 'Proficient' badge and rating interface on results page")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()