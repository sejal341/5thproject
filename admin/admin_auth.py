"""Admin Authentication Middleware.

Provides admin authentication and authorization functionality.
"""

import os
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash


def is_admin_authenticated():
    """Check if admin is currently authenticated."""
    return session.get('admin_authenticated', False)


def admin_required(view):
    """Decorator to require admin authentication for admin routes."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin_authenticated():
            flash("Admin access required. Please log in.", "error")
            return redirect(url_for('admin.admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verify admin credentials using environment variables.
    
    Admin credentials should be set as:
    - ADMIN_USERNAME: Admin username
    - ADMIN_PASSWORD: Admin password (hashed)
    
    If ADMIN_PASSWORD is plain text, it will be hashed for storage.
    """
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH') or os.getenv('ADMIN_PASSWORD')
    
    # If no password hash is set, use the plain password (for initial setup)
    if not admin_password_hash:
        return False
    
    # If ADMIN_PASSWORD was set (plain text), hash it for comparison
    from werkzeug.security import generate_password_hash
    if admin_password_hash == os.getenv('ADMIN_PASSWORD'):
        # This is the plain password, hash it for proper storage
        admin_password_hash = generate_password_hash(admin_password_hash)
        # In a real system, you'd want to update the environment variable
        # For now, we'll use the plain password for verification
    
    return (username == admin_username and 
            check_password_hash(admin_password_hash, password))
