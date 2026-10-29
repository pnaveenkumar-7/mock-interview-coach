import functools
import secrets
from flask import session, redirect, url_for, request, abort, render_template
from app.models import User


def generate_csrf_token():
    """
    Generates a secure random CSRF token and stores it in the user's session.
    If a token already exists in the session, reuses it.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf():
    """
    Validates the submitted CSRF token against the session token.
    Uses secrets.compare_digest() to prevent timing attacks.
    """
    submitted_token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    session_token = session.get("csrf_token")

    if not submitted_token or not session_token:
        abort(400, description="Missing CSRF token.")

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(str(submitted_token), str(session_token)):
        abort(400, description="Invalid CSRF token.")


def get_current_user():
    """
    Loads the currently authenticated user from the database based on session['user_id'].
    Returns None if no user is logged in or user does not exist.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    from app.extensions import db
    return db.session.get(User, user_id)


def login_required(view_func):
    """
    Decorator that requires a user to be logged in.
    Redirects unauthenticated users to the login page.
    """
    @functools.wraps(view_func)
    def decorated_view(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return decorated_view


def role_required(required_role):
    """
    Decorator that restricts access to users with a specific role (e.g., 'admin').
    Returns a 403 Forbidden page if the logged-in user lacks permission.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def decorated_view(*args, **kwargs):
            user = get_current_user()
            if not user:
                return redirect(url_for("auth.login"))

            if user.role != required_role:
                # User lacks the required role: render 403 page
                return render_template("403.html"), 403

            return view_func(*args, **kwargs)

        return decorated_view

    return decorator
