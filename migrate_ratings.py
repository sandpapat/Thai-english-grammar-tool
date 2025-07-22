#!/usr/bin/env python3
"""
Migration script to update existing ratings to the new multi-criteria format.
Maps old translation_rating to translation_accuracy and provides sensible defaults.
"""

from app import create_app
from app.models import db, Rating
from sqlalchemy import text

def migrate_ratings():
    """Migrate existing ratings to new schema"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all existing ratings using raw SQL to avoid model issues
            result = db.session.execute(text("""
                SELECT id, translation_rating, overall_quality_rating, 
                       translation_accuracy, translation_fluency, 
                       explanation_quality, educational_value
                FROM ratings
            """)).fetchall()
            
            if not result:
                print("No existing ratings to migrate.")
                return
            
            print(f"Found {len(result)} ratings to migrate...")
            
            migrated_count = 0
            for row in result:
                rating_id = row[0]
                old_translation = row[1]
                old_overall = row[2]
                existing_accuracy = row[3] if len(row) > 3 else None
                
                # Only migrate if new fields are not set
                if existing_accuracy is None:
                    # Calculate new values based on old ratings
                    if old_translation:
                        accuracy = old_translation
                        fluency = max(1, old_translation - 1)  # Slightly more critical
                    else:
                        accuracy = 3
                        fluency = 3
                    
                    if old_overall:
                        explanation = old_overall
                        educational = old_overall
                    else:
                        explanation = 3
                        educational = 3
                    
                    # Update using raw SQL
                    update_sql = text("""
                        UPDATE ratings 
                        SET translation_accuracy = :accuracy, 
                            translation_fluency = :fluency, 
                            explanation_quality = :explanation, 
                            educational_value = :educational,
                            issue_tags = :tags
                        WHERE id = :id
                    """)
                    
                    db.session.execute(update_sql, {
                        'accuracy': accuracy,
                        'fluency': fluency,
                        'explanation': explanation,
                        'educational': educational,
                        'tags': '[]',
                        'id': rating_id
                    })
                    migrated_count += 1
                    print(f"Migrated rating {rating_id}")
            
            # Commit all changes
            db.session.commit()
            print(f"\nSuccessfully migrated {migrated_count} ratings!")
            
            # Show summary
            print("\nMigration Summary:")
            print(f"Total ratings: {len(result)}")
            print(f"Migrated: {migrated_count}")
            print(f"Already migrated: {len(result) - migrated_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            raise

def add_new_columns():
    """Add new columns to the ratings table using raw SQL"""
    app = create_app()
    
    with app.app_context():
        try:
            # Add new columns using raw SQL to avoid model conflicts
            
            # Get current columns
            result = db.session.execute(text("PRAGMA table_info(ratings)")).fetchall()
            existing_columns = [row[1] for row in result]
            
            print(f"Existing columns: {existing_columns}")
            
            # Add new columns if they don't exist
            new_columns = {
                'translation_accuracy': 'INTEGER',
                'translation_fluency': 'INTEGER', 
                'explanation_quality': 'INTEGER',
                'educational_value': 'INTEGER',
                'issue_tags': 'TEXT'
            }
            
            for column_name, column_type in new_columns.items():
                if column_name not in existing_columns:
                    sql = f"ALTER TABLE ratings ADD COLUMN {column_name} {column_type}"
                    print(f"Adding column: {sql}")
                    db.session.execute(text(sql))
                    db.session.commit()
                else:
                    print(f"Column {column_name} already exists")
            
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