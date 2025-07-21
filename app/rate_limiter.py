"""
Rate limiting system for preventing abuse and managing concurrent requests.
Implements both per-user rate limiting and global request throttling.
"""

import time
import threading
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, current_user
from datetime import datetime, timedelta


class RateLimiter:
    """Thread-safe rate limiter with per-user and global limits"""
    
    def __init__(self, 
                 per_user_requests=3, 
                 per_user_window=60, 
                 global_requests=20, 
                 global_window=60,
                 min_interval=10):
        """
        Initialize rate limiter
        
        Args:
            per_user_requests: Max requests per user in time window
            per_user_window: Time window in seconds for per-user limit
            global_requests: Max global requests in time window
            global_window: Time window in seconds for global limit
            min_interval: Minimum seconds between requests from same user
        """
        self.per_user_requests = per_user_requests
        self.per_user_window = per_user_window
        self.global_requests = global_requests
        self.global_window = global_window
        self.min_interval = min_interval
        
        # User-specific request tracking
        self.user_requests = defaultdict(deque)
        self.user_last_request = {}
        
        # Global request tracking
        self.global_request_times = deque()
        
        # Request deduplication (prevent exact duplicate requests)
        self.user_request_cache = {}
        self.cache_expiry = 30  # seconds
        
        # Thread safety
        self.lock = threading.RLock()
        
        print(f"✓ Rate limiter initialized: {per_user_requests} req/user/{per_user_window}s, {global_requests} global/{global_window}s")
    
    def is_allowed(self, user_identifier, request_hash=None):
        """
        Check if request is allowed
        
        Args:
            user_identifier: Unique identifier for user (IP or user ID)
            request_hash: Hash of request content for duplicate detection
            
        Returns:
            tuple: (is_allowed, reason, retry_after_seconds)
        """
        with self.lock:
            current_time = time.time()
            
            # Clean old entries
            self._cleanup_old_entries(current_time)
            
            # Check for duplicate request
            if request_hash and self._is_duplicate_request(user_identifier, request_hash, current_time):
                return False, "Duplicate request detected", 5
            
            # Check minimum interval between requests from same user
            if user_identifier in self.user_last_request:
                time_since_last = current_time - self.user_last_request[user_identifier]
                if time_since_last < self.min_interval:
                    retry_after = self.min_interval - time_since_last
                    return False, f"Please wait {int(retry_after)} seconds before making another request", int(retry_after)
            
            # Check per-user rate limit
            user_times = self.user_requests[user_identifier]
            if len(user_times) >= self.per_user_requests:
                oldest_request = user_times[0]
                if current_time - oldest_request < self.per_user_window:
                    retry_after = self.per_user_window - (current_time - oldest_request)
                    return False, f"Too many requests. Try again in {int(retry_after)} seconds", int(retry_after)
            
            # Check global rate limit
            if len(self.global_request_times) >= self.global_requests:
                oldest_global = self.global_request_times[0]
                if current_time - oldest_global < self.global_window:
                    retry_after = self.global_window - (current_time - oldest_global)
                    return False, f"Server busy. Try again in {int(retry_after)} seconds", int(retry_after)
            
            # Record this request
            user_times.append(current_time)
            self.global_request_times.append(current_time)
            self.user_last_request[user_identifier] = current_time
            
            # Cache request hash to prevent duplicates
            if request_hash:
                self.user_request_cache[(user_identifier, request_hash)] = current_time
            
            return True, "Request allowed", 0
    
    def _cleanup_old_entries(self, current_time):
        """Remove old entries to prevent memory leaks"""
        # Clean user request times
        for user_id in list(self.user_requests.keys()):
            user_times = self.user_requests[user_id]
            while user_times and current_time - user_times[0] > self.per_user_window:
                user_times.popleft()
            
            # Remove empty deques
            if not user_times:
                del self.user_requests[user_id]
        
        # Clean global request times
        while self.global_request_times and current_time - self.global_request_times[0] > self.global_window:
            self.global_request_times.popleft()
        
        # Clean request cache
        expired_cache = []
        for (user_id, req_hash), timestamp in self.user_request_cache.items():
            if current_time - timestamp > self.cache_expiry:
                expired_cache.append((user_id, req_hash))
        
        for key in expired_cache:
            del self.user_request_cache[key]
    
    def _is_duplicate_request(self, user_identifier, request_hash, current_time):
        """Check if this is a duplicate request within the cache window"""
        cache_key = (user_identifier, request_hash)
        if cache_key in self.user_request_cache:
            last_time = self.user_request_cache[cache_key]
            if current_time - last_time < self.cache_expiry:
                return True
        return False
    
    def get_stats(self):
        """Get current rate limiter statistics"""
        with self.lock:
            current_time = time.time()
            self._cleanup_old_entries(current_time)
            
            return {
                'active_users': len(self.user_requests),
                'global_requests_in_window': len(self.global_request_times),
                'cached_requests': len(self.user_request_cache),
                'per_user_limit': self.per_user_requests,
                'global_limit': self.global_requests
            }


# Global rate limiter instance
rate_limiter = RateLimiter(
    per_user_requests=2,    # 2 requests per user
    per_user_window=60,     # per 60 seconds
    global_requests=10,     # 10 requests globally
    global_window=60,       # per 60 seconds  
    min_interval=15         # minimum 15 seconds between requests from same user
)


def rate_limit(f):
    """
    Decorator for rate limiting routes
    
    Usage:
        @app.route('/predict', methods=['POST'])
        @rate_limit
        def predict():
            return "Success"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Generate user identifier
        if current_user and current_user.is_authenticated:
            user_id = f"user_{current_user.id}"
        else:
            user_id = f"ip_{request.remote_addr}"
        
        # Generate request hash for duplicate detection
        request_data = request.form.get('thai_text', '') + request.path
        request_hash = hash(request_data)
        
        # Check rate limit
        is_allowed, reason, retry_after = rate_limiter.is_allowed(user_id, request_hash)
        
        if not is_allowed:
            print(f"Rate limit exceeded for {user_id}: {reason}")
            
            # For AJAX requests, return JSON
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': reason,
                    'retry_after': retry_after
                }), 429
            
            # For regular requests, return HTML error
            from flask import render_template, flash
            flash(f'Rate limit exceeded: {reason}', 'error')
            return render_template('index.html'), 429
        
        # Request is allowed, proceed
        return f(*args, **kwargs)
    
    return decorated_function


def get_rate_limit_info(user_identifier=None):
    """Get rate limit information for display to users"""
    if not user_identifier:
        if current_user and current_user.is_authenticated:
            user_identifier = f"user_{current_user.id}"
        else:
            user_identifier = f"ip_{request.remote_addr}"
    
    with rate_limiter.lock:
        current_time = time.time()
        rate_limiter._cleanup_old_entries(current_time)
        
        user_requests = len(rate_limiter.user_requests.get(user_identifier, []))
        global_requests = len(rate_limiter.global_request_times)
        
        # Calculate time until next request allowed
        next_allowed = 0
        if user_identifier in rate_limiter.user_last_request:
            time_since_last = current_time - rate_limiter.user_last_request[user_identifier]
            if time_since_last < rate_limiter.min_interval:
                next_allowed = rate_limiter.min_interval - time_since_last
        
        return {
            'user_requests': user_requests,
            'user_limit': rate_limiter.per_user_requests,
            'global_requests': global_requests,
            'global_limit': rate_limiter.global_requests,
            'next_allowed_in': max(0, int(next_allowed)),
            'min_interval': rate_limiter.min_interval
        }