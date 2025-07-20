#!/usr/bin/env python3
"""
Production-safe database migration script
This script should be run on the VM after deploying the updated code
"""

import os
import sys
import sqlite3
from pathlib import Path

def find_database():
    """Find the database file in the production environment"""
    possible_locations = [
        'instance/pseudocodes.db',
        'instance/database.db', 
        'database.db',
        'app.db',
        '/tmp/pseudocodes.db'
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            print(f"✅ Found database at: {location}")
            return location
    
    print("❌ No database found. Database locations checked:")
    for location in possible_locations:
        print(f"   - {location} {'✅' if os.path.exists(location) else '❌'}")
    
    return None

def backup_database(db_path):
    """Create a backup of the existing database"""
    backup_path = f"{db_path}.backup"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """Perform the database migration"""
    print("🚀 Starting production database migration...")
    
    # Find database
    db_path = find_database()
    if not db_path:
        print("❌ Cannot proceed without database file")
        return False
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current database schema...")
        
        # Check if pseudocodes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pseudocodes'")
        if not cursor.fetchone():
            print("❌ pseudocodes table not found")
            return False
        
        # Check if user_type column exists
        if check_column_exists(cursor, 'pseudocodes', 'user_type'):
            print("✅ user_type column already exists")
        else:
            print("🔧 Adding user_type column...")
            cursor.execute("""
                ALTER TABLE pseudocodes 
                ADD COLUMN user_type TEXT DEFAULT 'normal' NOT NULL
            """)
            print("✅ user_type column added")
        
        # Check if ratings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ratings'")
        if cursor.fetchone():
            print("✅ ratings table already exists")
        else:
            print("🔧 Creating ratings table...")
            cursor.execute("""
                CREATE TABLE ratings (
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
            print("✅ ratings table created")
        
        # Create indexes
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ratings_timestamp ON ratings (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pseudocodes_user_type ON pseudocodes (user_type)")
            print("✅ Database indexes created")
        except Exception as e:
            print(f"⚠️  Warning: Could not create some indexes: {e}")
        
        # Update existing users - make pseudocodes starting with 9 proficient
        cursor.execute("""
            UPDATE pseudocodes 
            SET user_type = 'proficient' 
            WHERE pseudocode LIKE '9%' AND user_type = 'normal'
        """)
        proficient_updated = cursor.rowcount
        
        # Commit all changes
        conn.commit()
        
        # Show final statistics
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'normal'")
        normal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pseudocodes WHERE user_type = 'proficient'")
        proficient_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ratings")
        rating_count = cursor.fetchone()[0]
        
        print(f"\n📊 Migration completed successfully!")
        print(f"   📁 Database: {db_path}")
        print(f"   💾 Backup: {backup_path or 'Not created'}")
        print(f"   👥 Normal users: {normal_count}")
        print(f"   🎯 Proficient users: {proficient_count}")
        print(f"   ⭐ Total ratings: {rating_count}")
        if proficient_updated > 0:
            print(f"   🔄 Updated {proficient_updated} users to proficient")
        
        print(f"\n🎉 Ready to restart Flask application!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        conn.close()
        
        # Offer to restore backup
        if backup_path and os.path.exists(backup_path):
            print(f"\n💡 To restore backup, run:")
            print(f"   cp {backup_path} {db_path}")
        
        return False

def create_test_users():
    """Create test users for verification"""
    db_path = find_database()
    if not db_path:
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        test_users = [
            ('12345', 'normal'),
            ('67890', 'normal'),
            ('90001', 'proficient'),
            ('91234', 'proficient')
        ]
        
        created_count = 0
        for pseudocode, user_type in test_users:
            # Check if user already exists
            cursor.execute("SELECT id FROM pseudocodes WHERE pseudocode = ?", (pseudocode,))
            if cursor.fetchone():
                print(f"⚠️  User {pseudocode} already exists")
                continue
            
            # Create user
            cursor.execute("""
                INSERT INTO pseudocodes (pseudocode, user_type, created_at, is_active)
                VALUES (?, ?, datetime('now'), 1)
            """, (pseudocode, user_type))
            created_count += 1
            print(f"✅ Created {user_type} user: {pseudocode}")
        
        if created_count > 0:
            conn.commit()
            print(f"✅ Created {created_count} test users")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Failed to create test users: {e}")

if __name__ == '__main__':
    print("🔧 Production Database Migration Tool")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 50)
        print("📝 Next Steps:")
        print("1. Restart your Flask application")
        print("2. Test login with existing users")
        print("3. Test with proficient users (pseudocodes starting with 9)")
        print("4. Verify rating interface appears for proficient users")
        
        response = input("\n❓ Create test users? (y/n): ").lower().strip()
        if response == 'y':
            create_test_users()
    else:
        print("\n❌ Migration failed. Please check errors above.")
        sys.exit(1)