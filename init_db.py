#!/usr/bin/env python3
"""
Database initialization script for adding pseudocodes
Usage: python init_db.py
"""

from app import app
from app.models import db, Pseudocode
import sys

def add_pseudocode(pseudocode):
    """Add a single pseudocode to the database"""
    try:
        with app.app_context():
            new_user = Pseudocode.create_pseudocode(pseudocode)
            print(f"✓ Added pseudocode: {pseudocode}")
            return True
    except ValueError as e:
        print(f"✗ Error adding {pseudocode}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def add_multiple_pseudocodes(codes_list):
    """Add multiple pseudocodes from a list"""
    success_count = 0
    for code in codes_list:
        if add_pseudocode(code.strip()):
            success_count += 1
    
    print(f"\nSummary: Added {success_count} out of {len(codes_list)} pseudocodes")

def list_all_pseudocodes():
    """List all existing pseudocodes"""
    with app.app_context():
        codes = Pseudocode.query.all()
        if codes:
            print("\nExisting pseudocodes:")
            print("-" * 30)
            for code in codes:
                status = "Active" if code.is_active else "Inactive"
                last_login = code.last_login.strftime("%Y-%m-%d %H:%M") if code.last_login else "Never"
                print(f"{code.pseudocode} - {status} - Last login: {last_login}")
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
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            code = input("Enter 5-digit pseudocode: ").strip()
            add_pseudocode(code)
        
        elif choice == '2':
            codes = input("Enter pseudocodes (comma-separated): ").strip()
            codes_list = [c.strip() for c in codes.split(',') if c.strip()]
            if codes_list:
                add_multiple_pseudocodes(codes_list)
            else:
                print("No valid codes provided")
        
        elif choice == '3':
            filename = input("Enter filename (one pseudocode per line): ").strip()
            try:
                with open(filename, 'r') as f:
                    codes_list = [line.strip() for line in f if line.strip()]
                if codes_list:
                    add_multiple_pseudocodes(codes_list)
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
            sample_codes = ['12345', '23456', '34567', '45678', '56789']
            print("\nAdding sample pseudocodes for testing...")
            add_multiple_pseudocodes(sample_codes)
        
        elif choice == '6':
            print("\nExiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()