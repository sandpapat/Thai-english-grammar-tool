#!/usr/bin/env python3
"""
Migration script to update existing ratings to the new multi-criteria format.
Maps old translation_rating to translation_accuracy and provides sensible defaults.
"""

from app import create_app
from app.models import db, Rating

def migrate_ratings():
    """Migrate existing ratings to new schema"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all existing ratings
            existing_ratings = Rating.query.all()
            
            if not existing_ratings:
                print("No existing ratings to migrate.")
                return
            
            print(f"Found {len(existing_ratings)} ratings to migrate...")
            
            migrated_count = 0
            for rating in existing_ratings:
                # Only migrate if new fields are not set
                if (hasattr(rating, 'translation_accuracy') and 
                    rating.translation_accuracy is None):
                    
                    # Map old translation_rating to translation_accuracy
                    if rating.translation_rating:
                        rating.translation_accuracy = rating.translation_rating
                        # Set fluency slightly lower (more critical)
                        rating.translation_fluency = max(1, rating.translation_rating - 1)
                    else:
                        # Default values if no old rating
                        rating.translation_accuracy = 3
                        rating.translation_fluency = 3
                    
                    # Map overall_quality_rating to explanation and educational value
                    if rating.overall_quality_rating:
                        rating.explanation_quality = rating.overall_quality_rating
                        rating.educational_value = rating.overall_quality_rating
                    else:
                        # Default values
                        rating.explanation_quality = 3
                        rating.educational_value = 3
                    
                    # Initialize empty issue tags
                    rating.issue_tags = []
                    
                    migrated_count += 1
                    print(f"Migrated rating {rating.id}")
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully migrated {migrated_count} ratings!")
            
            # Show summary
            print("\nMigration Summary:")
            print(f"Total ratings: {len(existing_ratings)}")
            print(f"Migrated: {migrated_count}")
            print(f"Already migrated: {len(existing_ratings) - migrated_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            raise

def add_new_columns():
    """Add new columns to the ratings table"""
    app = create_app()
    
    with app.app_context():
        try:
            # This will add the new columns if they don't exist
            db.create_all()
            print("Database schema updated successfully!")
        except Exception as e:
            print(f"Error updating schema: {str(e)}")
            raise

if __name__ == "__main__":
    print("Rating System Migration Script")
    print("==============================")
    
    # First, update the schema
    print("\n1. Updating database schema...")
    add_new_columns()
    
    # Then migrate existing data
    print("\n2. Migrating existing ratings...")
    migrate_ratings()
    
    print("\nMigration complete!")
    print("\nNote: The old fields (translation_rating, overall_quality_rating) are kept")
    print("for backward compatibility but will not be used for new ratings.")