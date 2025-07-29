#!/usr/bin/env python3
"""
Script to create an admin user for the Thaislate admin dashboard
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Admin

def create_admin_user():
    """Interactive script to create an admin user"""
    app = create_app()
    
    with app.app_context():
        print("\n=== Thaislate Admin User Creation ===\n")
        
        # Check if any admins exist
        existing_count = Admin.query.count()
        if existing_count > 0:
            print(f"Note: {existing_count} admin user(s) already exist.\n")
        
        # Get admin details
        username = input("Enter admin username: ").strip()
        if not username:
            print("Error: Username cannot be empty")
            return
        
        email = input("Enter admin email: ").strip()
        if not email or '@' not in email:
            print("Error: Invalid email address")
            return
        
        full_name = input("Enter full name (optional): ").strip()
        
        # Get password
        import getpass
        password = getpass.getpass("Enter password: ")
        if len(password) < 8:
            print("Error: Password must be at least 8 characters")
            return
        
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("Error: Passwords do not match")
            return
        
        # Ask about super admin status
        is_super = input("Grant super admin privileges? (y/N): ").strip().lower() == 'y'
        
        try:
            # Create the admin
            admin = Admin.create_admin(
                username=username,
                email=email,
                password=password,
                full_name=full_name if full_name else None,
                is_super_admin=is_super
            )
            
            print(f"\n✅ Admin user '{username}' created successfully!")
            print(f"   Email: {email}")
            print(f"   Super Admin: {'Yes' if is_super else 'No'}")
            print(f"\nYou can now login at: /admin/login\n")
            
        except ValueError as e:
            print(f"\nError: {e}")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_admin_user()