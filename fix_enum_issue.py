#!/usr/bin/env python3
"""
Quick fix for enum compatibility issue
Run this on your VM after pulling the updated code
"""

import os
import sqlite3

def find_database():
    """Find the database file"""
    possible_locations = [
        'instance/pseudocodes.db',
        'instance/database.db', 
        'database.db',
        'app.db'
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            print(f"✅ Found database at: {location}")
            return location
    
    print("❌ No database found")
    return None

def fix_enum_compatibility():
    """Fix the enum compatibility issue"""
    print("🔧 Fixing enum compatibility issue...")
    
    db_path = find_database()
    if not db_path:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if pseudocodes table exists and has user_type column
        cursor.execute("PRAGMA table_info(pseudocodes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_type' not in columns:
            print("📝 Adding user_type column...")
            cursor.execute("ALTER TABLE pseudocodes ADD COLUMN user_type TEXT DEFAULT 'normal' NOT NULL")
            print("✅ user_type column added")
        else:
            print("✅ user_type column already exists")
        
        # Ensure all user_type values are valid strings
        cursor.execute("UPDATE pseudocodes SET user_type = 'normal' WHERE user_type IS NULL OR user_type = ''")
        cursor.execute("UPDATE pseudocodes SET user_type = 'proficient' WHERE pseudocode LIKE '9%' AND user_type = 'normal'")
        
        # Check for invalid values and fix them
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type NOT IN ('normal', 'proficient')")
        invalid_count = cursor.fetchone()[0]
        
        if invalid_count > 0:
            print(f"🔧 Fixing {invalid_count} invalid user_type values...")
            cursor.execute("UPDATE pseudocodes SET user_type = 'normal' WHERE user_type NOT IN ('normal', 'proficient')")
        
        # Create ratings table if it doesn't exist
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
        print("✅ Ratings table ensured")
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pseudocodes_user_type ON pseudocodes (user_type)")
        
        conn.commit()
        
        # Show final statistics
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'normal'")
        normal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'proficient'")
        proficient_count = cursor.fetchone()[0]
        
        print(f"\n📊 Final Database State:")
        print(f"   👥 Normal users: {normal_count}")
        print(f"   🎯 Proficient users: {proficient_count}")
        print(f"   📁 Database: {db_path}")
        
        conn.close()
        
        print(f"\n🎉 Enum compatibility fixed successfully!")
        print(f"✅ Ready to restart Flask application")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    print("🔧 Enum Compatibility Fix Tool")
    print("=" * 40)
    
    success = fix_enum_compatibility()
    
    if success:
        print("\n📋 Next Steps:")
        print("1. Restart your Flask application")
        print("2. Test login with any existing user")
        print("3. Users with pseudocodes starting with '9' will be proficient")
        print("4. All other users will be normal")
    else:
        print("\n❌ Fix failed. Please check the error messages above.")