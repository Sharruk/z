from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def allowed_roles(roles):
    """
    Decorator to check if current user has required role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'warning')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
