/**
 * Session Management and Activity Tracking JavaScript
 * Handles session timeout warnings and user activity monitoring
 */

class SessionManager {
    constructor() {
        this.sessionTimeoutMinutes = 15; // 15 minutes timeout
        this.warningTimeMinutes = 2;     // Warn 2 minutes before timeout
        this.checkInterval = 30000;      // Check every 30 seconds
        this.lastActivity = Date.now();
        this.sessionTimer = null;
        this.warningShown = false;
        
        this.init();
    }
    
    init() {
        // Track user activity
        this.trackUserActivity();
        
        // Start session monitoring
        this.startSessionMonitoring();
        
        // Handle visibility change (tab switching)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.resetActivityTimer();
            }
        });
    }
    
    trackUserActivity() {
        // Track various user interactions
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                this.resetActivityTimer();
            }, { passive: true });
        });
    }
    
    resetActivityTimer() {
        this.lastActivity = Date.now();
        this.warningShown = false;
        
        // Remove any existing warning
        this.removeSessionWarning();
    }
    
    startSessionMonitoring() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
        
        this.sessionTimer = setInterval(() => {
            this.checkSessionStatus();
        }, this.checkInterval);
    }
    
    checkSessionStatus() {
        const now = Date.now();
        const timeSinceActivity = (now - this.lastActivity) / 1000 / 60; // minutes
        
        const warningThreshold = this.sessionTimeoutMinutes - this.warningTimeMinutes;
        
        if (timeSinceActivity >= this.sessionTimeoutMinutes) {
            // Session has expired - redirect to login
            this.handleSessionExpiry();
        } else if (timeSinceActivity >= warningThreshold && !this.warningShown) {
            // Show warning
            this.showSessionWarning();
        }
    }
    
    showSessionWarning() {
        this.warningShown = true;
        
        // Create warning toast
        const toast = this.createSessionWarningToast();
        document.body.appendChild(toast);
        
        // Show toast using Bootstrap
        const bsToast = new bootstrap.Toast(toast, {
            autohide: false // Don't auto-hide, let user dismiss
        });
        bsToast.show();
        
        console.log('Session warning displayed');
    }
    
    createSessionWarningToast() {
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.id = 'sessionWarningToast';
        
        toast.innerHTML = `
            <div class="toast-header bg-warning text-dark">
                <i class="bi bi-clock-history me-2"></i>
                <strong class="me-auto">Session Expiring Soon</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <p class="mb-2">Your session will expire in 2 minutes due to inactivity.</p>
                <button class="btn btn-sm btn-primary" onclick="sessionManager.extendSession()">
                    <i class="bi bi-arrow-clockwise me-1"></i>Stay Active
                </button>
            </div>
        `;
        
        return toast;
    }
    
    removeSessionWarning() {
        const existingToast = document.getElementById('sessionWarningToast');
        if (existingToast) {
            const bsToast = bootstrap.Toast.getInstance(existingToast);
            if (bsToast) {
                bsToast.hide();
            }
            setTimeout(() => {
                existingToast.remove();
            }, 500);
        }
    }
    
    extendSession() {
        // Reset activity and remove warning
        this.resetActivityTimer();
        
        // Make a lightweight request to extend session on server
        fetch('/api/extend-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Session extended successfully');
                this.showExtensionSuccess();
            }
        })
        .catch(error => {
            console.error('Failed to extend session:', error);
        });
    }
    
    showExtensionSuccess() {
        // Show brief success message
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        toast.innerHTML = `
            <div class="toast-header bg-success text-white">
                <i class="bi bi-check-circle me-2"></i>
                <strong class="me-auto">Session Extended</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                Your session has been extended for another 15 minutes.
            </div>
        `;
        
        document.body.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        // Auto-remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    handleSessionExpiry() {
        // Stop monitoring
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
        
        // Show expiry message and redirect
        this.showExpiryMessage();
    }
    
    showExpiryMessage() {
        // Create modal for session expiry
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'sessionExpiryModal';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-sm">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-triangle me-2"></i>Session Expired
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <p>Your session has expired due to 15 minutes of inactivity.</p>
                        <p class="text-muted mb-0">You will be redirected to the login page.</p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary" onclick="window.location.href='/login'">
                            <i class="bi bi-box-arrow-in-right me-2"></i>Login Again
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Auto-redirect after 5 seconds
        setTimeout(() => {
            window.location.href = '/login';
        }, 5000);
    }
    
    destroy() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
        this.removeSessionWarning();
    }
}

// Activity Tracker for analytics
class ActivityTracker {
    constructor() {
        this.pageStartTime = Date.now();
        this.init();
    }
    
    init() {
        // Track page views
        this.trackPageView();
        
        // Track page leave
        window.addEventListener('beforeunload', () => {
            this.trackPageLeave();
        });
        
        // Track form submissions (for analytics)
        this.trackFormSubmissions();
    }
    
    trackPageView() {
        // Only track if user is logged in
        if (document.body.dataset.userLoggedIn === 'true') {
            this.sendActivityData('page_view', {
                page: window.location.pathname,
                referrer: document.referrer,
                timestamp: new Date().toISOString()
            });
        }
    }
    
    trackPageLeave() {
        const timeSpent = Math.round((Date.now() - this.pageStartTime) / 1000);
        
        if (document.body.dataset.userLoggedIn === 'true' && timeSpent > 5) {
            // Use sendBeacon for reliable delivery on page leave
            this.sendActivityBeacon('page_leave', {
                page: window.location.pathname,
                time_spent_seconds: timeSpent,
                timestamp: new Date().toISOString()
            });
        }
    }
    
    trackFormSubmissions() {
        // Track translation form submissions
        const translateForm = document.getElementById('translateForm');
        if (translateForm) {
            translateForm.addEventListener('submit', (e) => {
                const formData = new FormData(translateForm);
                const thaiText = formData.get('thai_text');
                
                if (thaiText && thaiText.trim().length > 0) {
                    this.sendActivityData('form_submit', {
                        form: 'translation',
                        input_length: thaiText.length,
                        timestamp: new Date().toISOString()
                    });
                }
            });
        }
    }
    
    sendActivityData(activityType, data) {
        // Don't send if not logged in
        if (document.body.dataset.userLoggedIn !== 'true') {
            return;
        }
        
        fetch('/api/track-activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                activity_type: activityType,
                data: data
            })
        })
        .catch(error => {
            console.debug('Activity tracking failed:', error);
        });
    }
    
    sendActivityBeacon(activityType, data) {
        // Use sendBeacon for page leave events (more reliable)
        if (navigator.sendBeacon && document.body.dataset.userLoggedIn === 'true') {
            const payload = JSON.stringify({
                activity_type: activityType,
                data: data
            });
            
            navigator.sendBeacon('/api/track-activity', payload);
        }
    }
}

// Initialize managers when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize for logged-in users
    const userLoggedIn = document.body.dataset.userLoggedIn === 'true';
    
    if (userLoggedIn) {
        // Global session manager
        window.sessionManager = new SessionManager();
        
        // Activity tracker
        window.activityTracker = new ActivityTracker();
        
        console.log('Session management and activity tracking initialized');
    } else {
        console.log('Session management skipped - user not logged in');
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.sessionManager) {
        window.sessionManager.destroy();
    }
});