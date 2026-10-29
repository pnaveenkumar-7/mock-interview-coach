import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
load_dotenv()


class Config:
    """
    Application configuration class.
    Reads sensitive settings and configuration options from environment variables.
    """
    # Secret key used for signing session cookies and security tokens
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key-change-in-production")

    # Database URI for SQLAlchemy; defaults to SQLite inside the instance folder
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")

    # Disable SQLAlchemy event tracking overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings for session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
