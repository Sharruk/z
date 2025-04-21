from functools import wraps
from flask import redirect, url_for, flash, session, request
from flask_login import current_user

def role_required(role):
    """
    Custom decorator for role-based access control
    Args:
        role (str): The required role ('customer', 'restaurant', or 'delivery')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                session['next'] = request.url
                return redirect(url_for('login'))
            
            if current_user.role != role:
                flash(f'Access denied. You must be a {role} to view this page.', 'danger')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
