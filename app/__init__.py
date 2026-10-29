import os
from flask import Flask, jsonify, render_template, g
from config import Config
from app.extensions import db


def create_app(config_class=Config, test_config=None):
    """
    Application factory pattern.
    Creates, configures, and returns an instance of the Flask application.
    Supports test_config for in-memory testing.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Apply test configuration overrides if provided (e.g., in-memory SQLite)
    if test_config:
        app.config.update(test_config)

    # Ensure the instance folder exists if using file-based SQLite
    if not app.config.get("TESTING"):
        os.makedirs(app.instance_path, exist_ok=True)

    # Initialize SQLAlchemy database with the application
    db.init_app(app)

    # Import models so SQLAlchemy metadata registers all tables
    from app import models  # noqa: F401

    # Automatically create database tables if they do not exist
    with app.app_context():
        db.create_all()

    # Context processor to inject CSRF generator and current_user into all templates
    @app.context_processor
    def inject_template_globals():
        from app.auth_utils import generate_csrf_token, get_current_user
        return {
            "csrf_token": generate_csrf_token,
            "current_user": get_current_user()
        }

    # Before request hook to load current_user into Flask's 'g' object
    @app.before_request
    def load_user():
        from app.auth_utils import get_current_user
        g.current_user = get_current_user()

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    # Health check route
    @app.route("/health")
    def health_check():
        """
        Health check endpoint to verify that the server is up and running.
        """
        return jsonify({"status": "ok"})

    # Home route: redirects to appropriate landing page or login
    @app.route("/")
    def index():
        from app.auth_utils import get_current_user
        from flask import redirect, url_for
        user = get_current_user()
        if not user:
            return redirect(url_for("auth.login"))
        if user.role == "admin":
            return redirect(url_for("admin.admin_index"))
        return redirect(url_for("interview.start_interview"))

    # Register blueprints for modular structure
    from app.routes.auth import auth_bp
    from app.routes.interview import interview_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    return app
