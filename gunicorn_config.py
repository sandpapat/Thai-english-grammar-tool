"""
Gunicorn configuration for Thai-English Grammar Learning Tool
"""

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - Optimized for heavy ML models
workers = 2  # Reduced from 4 - heavy models need more memory per worker
worker_class = "sync"
worker_connections = 1000
timeout = 90  # Increased from 30 - ML inference can be slow
keepalive = 2

# Restart workers more frequently to prevent memory leaks from large models
max_requests = 50  # Reduced from 1000 - prevents memory accumulation
max_requests_jitter = 10  # Reduced proportionally

# Load application code before the worker processes are forked
preload_app = True

# Logging - Enhanced for production monitoring
loglevel = 'info'
accesslog = '-'
errorlog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Enable detailed request logging for debugging concurrency issues
capture_output = True

# Process naming
proc_name = 'thai-english-app'

# Server mechanics
daemon = False  # Set to True for production background running
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# Worker process management - Enhanced stability
worker_tmp_dir = '/dev/shm'  # Use shared memory for better performance
graceful_timeout = 60  # Time to wait for graceful worker shutdown
worker_proc_start_timeout = 120  # Time to wait for worker to start (ML models are slow to load)

# Memory and resource management
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8192

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'