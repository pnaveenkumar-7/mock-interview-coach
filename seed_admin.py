import os
import sys
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User


def seed_admin():
    """
    Seeds a default Admin / Placement Officer user from .env variables.
    Refuses to run if ADMIN_PASSWORD is set to default 'CHANGE_ME' or shorter than 8 chars.
    """
    admin_name = os.environ.get("ADMIN_NAME", "Admin Officer").strip()
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@college.edu").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()

    # Security check: Refuse default or weak password
    if not admin_password or admin_password == "CHANGE_ME":
        print("[ERROR] ADMIN_PASSWORD in .env is still set to 'CHANGE_ME'.")
        print("Please edit your .env file and set a secure password before seeding.")
        sys.exit(1)

    if len(admin_password) < 8:
        print(f"[ERROR] ADMIN_PASSWORD must be at least 8 characters long (got {len(admin_password)}).")
        print("Please update ADMIN_PASSWORD in your .env file.")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        # Check if the admin user already exists
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            print(f"[INFO] Admin user '{admin_email}' already exists (Role: {existing_user.role}).")
            return

        # Create new admin user
        admin = User(
            name=admin_name,
            email=admin_email,
            role="admin"
        )
        admin.set_password(admin_password)

        db.session.add(admin)
        db.session.commit()

        print(f"[SUCCESS] Admin account created successfully!")
        print(f" - Name:  {admin_name}")
        print(f" - Email: {admin_email}")
        print(f" - Role:  admin")


if __name__ == "__main__":
    seed_admin()

