import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import User
from app.auth_utils import validate_csrf, get_current_user

# Create Blueprint for authentication
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Email validation regex pattern
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Student registration endpoint.
    Only creates student accounts. Placement Officers/Admins are seeded securely.
    """
    # If user is already logged in, redirect them
    if get_current_user():
        return redirect(url_for("interview.start_interview"))

    if request.method == "POST":
        validate_csrf()

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation checks
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        # Create new student user (Admins are NEVER created via registration)
        new_student = User(
            name=name,
            email=email,
            role="student"
        )
        new_student.set_password(password)

        db.session.add(new_student)
        db.session.commit()

        flash("Registration successful! Please log in to begin.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login endpoint for both students and placement officers/admins.
    Uses generic error messages to prevent email enumeration.
    """
    # If user is already logged in, route to appropriate landing page
    current = get_current_user()
    if current:
        if current.role == "admin":
            return redirect(url_for("admin.admin_index"))
        return redirect(url_for("interview.start_interview"))

    if request.method == "POST":
        validate_csrf()

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email)

        user = User.query.filter_by(email=email).first()

        # Check user existence and verify hashed password
        if not user or not user.check_password(password):
            # Deliberately generic message: does not reveal if email or password was wrong
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email)

        # Security practice: clear any existing session data before storing new user session
        session.clear()
        session["user_id"] = user.id

        flash(f"Welcome back, {user.name}!", "success")

        # Route by role
        if user.role == "admin":
            return redirect(url_for("admin.admin_index"))
        return redirect(url_for("interview.start_interview"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Logout endpoint.
    Restricted to POST requests with CSRF validation to protect against forced logout CSRF.
    """
    validate_csrf()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
