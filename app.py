#!/usr/bin/env python3
"""
Main application entry point
"""
import os
from app import create_app

if __name__ == '__main__':
    # Create Flask app using factory pattern
    app = create_app()
    
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)