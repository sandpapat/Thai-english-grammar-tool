#!/usr/bin/env python3
"""
Database initialization script for adding pseudocodes
Usage: python init_db.py
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import db, Pseudocode, UserType
import os

# Create a minimal Flask app just for database operations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pseudocodes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with this app
db.init_app(app)

def add_pseudocode(pseudocode, user_type=None):
    """Add a single pseudocode to the database"""
    try:
        with app.app_context():
            # If user_type is provided, use it; otherwise let the model auto-determine
            if user_type:
                new_user = Pseudocode.create_pseudocode(pseudocode, user_type)
            else:
                new_user = Pseudocode.create_pseudocode(pseudocode)
            print(f"✓ Added pseudocode: {pseudocode} ({new_user.user_type})")
            return True
    except ValueError as e:
        print(f"✗ Error adding {pseudocode}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def get_user_type_choice():
    """Get user type choice from user input"""
    while True:
        print("\nSelect user type:")
        print("1. Normal user")
        print("2. Proficient user")
        
        choice = input("Enter choice (1-2, default=1): ").strip()
        if choice == '' or choice == '1':
            return UserType.NORMAL
        elif choice == '2':
            return UserType.PROFICIENT
        else:
            print("Invalid choice. Please enter 1 or 2.")

def add_multiple_pseudocodes(codes_list, user_type=None):
    """Add multiple pseudocodes from a list"""
    success_count = 0
    for code in codes_list:
        if add_pseudocode(code.strip(), user_type):
            success_count += 1
    
    print(f"\nSummary: Added {success_count} out of {len(codes_list)} pseudocodes")

def list_all_pseudocodes():
    """List all existing pseudocodes"""
    with app.app_context():
        codes = Pseudocode.query.all()
        if codes:
            print("\nExisting pseudocodes:")
            print("-" * 60)
            print(f"{'Code':<8} {'Type':<12} {'Status':<8} {'Last Login':<20}")
            print("-" * 60)
            for code in codes:
                status = "Active" if code.is_active else "Inactive"
                last_login = code.last_login.strftime("%Y-%m-%d %H:%M") if code.last_login else "Never"
                user_type_display = code.user_type.capitalize()
                print(f"{code.pseudocode:<8} {user_type_display:<12} {status:<8} {last_login:<20}")
        else:
            print("\nNo pseudocodes found in database")

def main():
    """Main function for interactive use"""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database initialized successfully")
    
    while True:
        print("\n" + "="*50)
        print("Pseudocode Management System")
        print("="*50)
        print("1. Add single pseudocode")
        print("2. Add multiple pseudocodes (comma-separated)")
        print("3. Add pseudocodes from file")
        print("4. List all pseudocodes")
        print("5. Add sample pseudocodes for testing")
        print("6. Exit")
        print("\nNote: Pseudocodes must be exactly 5 characters (letters and numbers only)")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            code = input("Enter 5-character pseudocode: ").strip().upper()
            user_type = get_user_type_choice()
            add_pseudocode(code, user_type)
        
        elif choice == '2':
            codes = input("Enter pseudocodes (comma-separated): ").strip()
            codes_list = [c.strip() for c in codes.split(',') if c.strip()]
            if codes_list:
                user_type = get_user_type_choice()
                add_multiple_pseudocodes(codes_list, user_type)
            else:
                print("No valid codes provided")
        
        elif choice == '3':
            filename = input("Enter filename (one pseudocode per line): ").strip()
            try:
                with open(filename, 'r') as f:
                    codes_list = [line.strip() for line in f if line.strip()]
                if codes_list:
                    user_type = get_user_type_choice()
                    add_multiple_pseudocodes(codes_list, user_type)
                else:
                    print("No valid codes found in file")
            except FileNotFoundError:
                print(f"File '{filename}' not found")
            except Exception as e:
                print(f"Error reading file: {e}")
        
        elif choice == '4':
            list_all_pseudocodes()
        
        elif choice == '5':
            # Add sample pseudocodes for testing
            print("\nAdding sample pseudocodes for testing...")
            print("Adding normal users:")
            normal_codes = ['12345', 'USER1', 'STU2A', 'TEST1', 'ABC12']
            add_multiple_pseudocodes(normal_codes, UserType.NORMAL)
            
            print("\nAdding proficient users (randomized codes):")
            proficient_codes = ['67890', 'PRO1A', 'ADV23', 'EXP45', 'SKILL']
            add_multiple_pseudocodes(proficient_codes, UserType.PROFICIENT)
        
        elif choice == '6':
            print("\nExiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()