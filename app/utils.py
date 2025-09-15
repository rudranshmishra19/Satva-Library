import logging
from functools import wraps
from flask import session, flash, redirect

# Configure logging for your app (adjust level as needed)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
