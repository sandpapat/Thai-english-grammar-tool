#!/bin/bash

# Thai-English Grammar Learning Tool Deployment Script
# This script helps deploy the application in production

set -e  # Exit on any error

echo "🚀 Starting Thai-English App Deployment"

# Configuration
APP_DIR="/home/ubuntu/thai-english-app"
SERVICE_NAME="thai-english-app"
USER="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (needed for systemd operations)
if [ "$EUID" -ne 0 ]; then
    print_error "This script needs to be run with sudo for systemd operations"
    echo "Usage: sudo ./deploy.sh"
    exit 1
fi

# Create application directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    print_status "Creating application directory: $APP_DIR"
    mkdir -p "$APP_DIR"
    chown -R $USER:$USER "$APP_DIR"
fi

# Copy application files (assumes script is run from project directory)
print_status "Copying application files..."
cp -r app/ config.py gunicorn_config.py app.py requirements.txt data/ docs/ "$APP_DIR/"
chown -R $USER:$USER "$APP_DIR"

# Set up virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u $USER python3 -m venv "$APP_DIR/venv"
fi

# Install dependencies
print_status "Installing Python dependencies..."
sudo -u $USER "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u $USER "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Set up database
print_status "Setting up database..."
cd "$APP_DIR"
sudo -u $USER "$APP_DIR/venv/bin/python" -c "
from app import create_app
app = create_app()
app.app_context().push()
from app.models import db
db.create_all()
print('Database tables created successfully')
"

# Install systemd service
print_status "Installing systemd service..."
cp thai-english-app.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
print_status "Enabling and starting service..."
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# Wait a moment for service to start
sleep 5

# Check service status
if systemctl is-active --quiet $SERVICE_NAME; then
    print_success "Service is running successfully!"
    
    # Show health check
    print_status "Testing health check endpoint..."
    if curl -s http://localhost:5000/health > /dev/null; then
        print_success "Health check passed!"
    else
        print_warning "Health check endpoint not responding yet (may still be loading models)"
    fi
    
    # Show service status
    print_status "Service status:"
    systemctl status $SERVICE_NAME --no-pager -l
    
else
    print_error "Service failed to start!"
    print_status "Service logs:"
    journalctl -u $SERVICE_NAME --no-pager -l
    exit 1
fi

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  - Check status: systemctl status $SERVICE_NAME"
echo "  - View logs: journalctl -u $SERVICE_NAME -f"
echo "  - Restart service: systemctl restart $SERVICE_NAME"
echo "  - Health check: curl http://localhost:5000/health"
echo "  - Rate limit info: curl http://localhost:5000/api/rate-limit-info"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Configure your web server (nginx/apache) to proxy to port 5000"
echo "  2. Set up SSL certificates"
echo "  3. Configure firewall rules"
echo "  4. Set up log rotation"
echo "  5. Configure monitoring/alerting"
echo ""
echo -e "${GREEN}Application is running at: http://localhost:5000${NC}"