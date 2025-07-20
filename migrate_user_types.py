#!/usr/bin/env python3
"""
Database migration script to add user_type column to existing pseudocodes table
"""

import os
import sys
import sqlite3

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_database_path():
    """Get the path to the SQLite database"""
    # Check common database locations
    possible_paths = [
        'instance/pseudocodes.db',
        'instance/database.db',
        'database.db',
        'app.db',
        'instance/app.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, check in instance directory
    instance_dir = 'instance'
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    return 'instance/pseudocodes.db'

def migrate_add_user_type():
    """Add user_type column to existing pseudocodes table"""
    db_path = get_database_path()
    print(f"🔍 Using database: {db_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user_type column exists
        cursor.execute("PRAGMA table_info(pseudocodes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_type' in columns:
            print("✅ user_type column already exists")
        else:
            print("🔄 Adding user_type column to pseudocodes table...")
            
            # Add the user_type column with default value 'normal'
            cursor.execute("""
                ALTER TABLE pseudocodes 
                ADD COLUMN user_type TEXT DEFAULT 'normal' NOT NULL
            """)
            
            print("✅ user_type column added successfully")
        
        # Update users with pseudocodes starting with 9 to be proficient
        cursor.execute("""
            UPDATE pseudocodes 
            SET user_type = 'proficient' 
            WHERE pseudocode LIKE '9%'
        """)
        
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"✅ Updated {updated_count} users to proficient type (pseudocodes starting with 9)")
        
        # Create the ratings table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                input_thai TEXT NOT NULL,
                translation_text TEXT NOT NULL,
                translation_rating INTEGER NOT NULL,
                overall_quality_rating INTEGER NOT NULL,
                comments TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES pseudocodes (id)
            )
        """)
        
        print("✅ Ratings table created/verified")
        
        # Create index on user_id for ratings
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings (user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ratings_timestamp ON ratings (timestamp)
        """)
        
        print("✅ Database indexes created")
        
        # Commit changes
        conn.commit()
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'normal'")
        normal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'proficient'")
        proficient_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ratings")
        rating_count = cursor.fetchone()[0]
        
        print(f"\n📊 Database Statistics:")
        print(f"   Normal users: {normal_count}")
        print(f"   Proficient users: {proficient_count}")
        print(f"   Total ratings: {rating_count}")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"\n📋 Test Instructions:")
        print(f"   1. Restart the Flask application")
        print(f"   2. Log in with a normal user (pseudocodes 00001-89999)")
        print(f"   3. Log in with a proficient user (pseudocodes starting with 9)")
        print(f"   4. Check navigation shows correct user type badges")
        print(f"   5. Proficient users should see rating interface on results page")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == '__main__':
    migrate_add_user_type()