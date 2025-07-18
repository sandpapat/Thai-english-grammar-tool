# Deployment Guide for Google Cloud VM

## Prerequisites

1. **Google Cloud VM** with Ubuntu/Debian
2. **Python 3.8+** installed
3. **Git** installed
4. **Nginx** (for production deployment)

## Step 1: Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd Thai-english-grammar-tool

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Environment Configuration

Create a `.env` file:

```bash
# Create environment file
cat > .env << EOF
SECRET_KEY=your-super-secret-key-here-change-this-in-production
DATABASE_URL=sqlite:///pseudocodes.db
FLASK_ENV=production
EOF
```

## Step 3: Database Setup

```bash
# Initialize database
python -c "from app import create_app; app = create_app('production'); app.app_context().push(); from app.models import db; db.create_all()"

# Or run the init script if you have one
python init_db.py
```

## Step 4: Test Local Setup

```bash
# Test the application
python app.py
```

The application should start on `http://0.0.0.0:5000`

## Step 5: Production Deployment with Gunicorn

### Install Gunicorn (already in requirements.txt)

```bash
pip install gunicorn
```

### Create Gunicorn Configuration

Create `gunicorn_config.py`:

```python
# gunicorn_config.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Run with Gunicorn

```bash
# Run in production mode
gunicorn -c gunicorn_config.py app:app
```

## Step 6: Configure Nginx (Recommended for Production)

### Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### Create Nginx Configuration

Create `/etc/nginx/sites-available/thai-english-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /path/to/your/app/app/static;  # Update path
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable the Site

```bash
sudo ln -s /etc/nginx/sites-available/thai-english-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: Create Systemd Service

Create `/etc/systemd/system/thai-english-app.service`:

```ini
[Unit]
Description=Thai-English Grammar Learning Tool
After=network.target

[Service]
User=your-username
Group=your-group
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/app/venv/bin"
ExecStart=/path/to/your/app/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable thai-english-app
sudo systemctl start thai-english-app
sudo systemctl status thai-english-app
```

## Step 8: Configure Firewall

```bash
# Allow HTTP traffic
sudo ufw allow 80
sudo ufw allow 443  # If you plan to use HTTPS
sudo ufw enable
```

## Step 9: SSL Certificate (Optional but Recommended)

### Using Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Troubleshooting

### Check Application Logs

```bash
# Check gunicorn logs
sudo journalctl -u thai-english-app -f

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

1. **Port already in use**: Change port in gunicorn_config.py
2. **Permission denied**: Check file permissions and user ownership
3. **Database errors**: Ensure database is initialized properly
4. **Missing models**: Check if model files exist in the models directory

## Performance Optimization

1. **Enable gzip compression in Nginx**
2. **Set up proper caching headers**
3. **Use Redis for session storage** (optional)
4. **Monitor with tools like htop, iostat**

## Security Considerations

1. **Change default secret key**
2. **Use HTTPS in production**
3. **Regular security updates**
4. **Firewall configuration**
5. **Rate limiting** (can be added to Nginx)

## Monitoring

Consider setting up monitoring with:
- **Prometheus + Grafana**
- **New Relic**
- **DataDog**
- **Basic server monitoring with htop, iostat**

## Backup Strategy

1. **Database backups**: Regular SQLite database backups
2. **Application backups**: Code repository backups
3. **Configuration backups**: Nginx, systemd service files