import re
from app.models import User
from app.extensions import db


def extract_csrf_token(response):
    """
    Helper function to parse the CSRF token rendered in HTML forms.
    Validates that real CSRF tokens are issued and processed in tests.
    """
    html = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', html)
    assert match is not None, f"CSRF token not found in response HTML: {html[:300]}"
    return match.group(1)


def test_student_registration_success(client, app):
    """
    Test student registration with valid data.
    Verifies that the account is created with role='student' and redirected to login.
    """
    # 1. Fetch registration form to get CSRF token
    res = client.get("/auth/register")
    assert res.status_code == 200
    token = extract_csrf_token(res)

    # 2. Submit valid registration
    res = client.post("/auth/register", data={
        "csrf_token": token,
        "name": "Alice Smith",
        "email": " Alice.Smith@Example.com ",  # Test space stripping & lowercase
        "password": "Password123",
        "confirm_password": "Password123"
    }, follow_redirects=True)

    assert res.status_code == 200
    assert "Registration successful!" in res.get_data(as_text=True)

    # 3. Verify in database
    with app.app_context():
        user = User.query.filter_by(email="alice.smith@example.com").first()
        assert user is not None
        assert user.name == "Alice Smith"
        assert user.role == "student"
        assert user.check_password("Password123") is True


def test_registration_duplicate_email(client):
    """
    Test that registering with an existing email is rejected.
    """
    res = client.get("/auth/register")
    token = extract_csrf_token(res)

    # First registration
    client.post("/auth/register", data={
        "csrf_token": token,
        "name": "First User",
        "email": "duplicate@example.com",
        "password": "Password123",
        "confirm_password": "Password123"
    })

    # Second registration with identical email
    res = client.get("/auth/register")
    token = extract_csrf_token(res)
    res2 = client.post("/auth/register", data={
        "csrf_token": token,
        "name": "Second User",
        "email": "DUPLICATE@example.com",
        "password": "Password123",
        "confirm_password": "Password123"
    })

    assert "An account with this email already exists." in res2.get_data(as_text=True)


def test_registration_short_password(client):
    """
    Test that passwords under 8 characters are rejected.
    """
    res = client.get("/auth/register")
    token = extract_csrf_token(res)

    res = client.post("/auth/register", data={
        "csrf_token": token,
        "name": "Short Pass User",
        "email": "short@example.com",
        "password": "short",
        "confirm_password": "short"
    })

    assert "Password must be at least 8 characters long." in res.get_data(as_text=True)


def test_login_success_student(client, app):
    """
    Test student login success:
    - Session stores only user_id
    - Redirects to /interview/start
    """
    # Create student
    with app.app_context():
        student = User(name="Bob Jones", email="bob@example.com", role="student")
        student.set_password("StudentPass123")
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    res = client.get("/auth/login")
    token = extract_csrf_token(res)

    # Submit login with mixed case and leading/trailing spaces
    res = client.post("/auth/login", data={
        "csrf_token": token,
        "email": "  BOB@Example.com  ",
        "password": "StudentPass123"
    })

    # Should redirect to interview start page
    assert res.status_code == 302
    assert "/interview/start" in res.headers["Location"]

    # Verify session contents
    with client.session_transaction() as sess:
        assert sess.get("user_id") == student_id


def test_login_success_admin(client, app):
    """
    Test admin login success:
    - Redirects to /admin/
    """
    # Create admin
    with app.app_context():
        admin = User(name="Placement Admin", email="admin@college.edu", role="admin")
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()

    res = client.get("/auth/login")
    token = extract_csrf_token(res)

    res = client.post("/auth/login", data={
        "csrf_token": token,
        "email": "admin@college.edu",
        "password": "AdminPass123"
    })

    # Should redirect to admin dashboard
    assert res.status_code == 302
    assert "/admin/" in res.headers["Location"]


def test_login_failure_generic_message(client, app):
    """
    Test that invalid credentials produce a generic error message
    without revealing whether the email or password was wrong.
    """
    # Create existing student
    with app.app_context():
        user = User(name="Charlie", email="charlie@example.com", role="student")
        user.set_password("CorrectPass123")
        db.session.add(user)
        db.session.commit()

    # Case 1: Wrong password
    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    res_wrong_pw = client.post("/auth/login", data={
        "csrf_token": token,
        "email": "charlie@example.com",
        "password": "WrongPassword!"
    })
    assert "Invalid email or password." in res_wrong_pw.get_data(as_text=True)

    # Case 2: Non-existent email
    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    res_wrong_email = client.post("/auth/login", data={
        "csrf_token": token,
        "email": "doesnotexist@example.com",
        "password": "CorrectPass123"
    })
    assert "Invalid email or password." in res_wrong_email.get_data(as_text=True)

    # Verify user_id is NOT in session
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logout_clears_session(client, app):
    """
    Test logout via POST with CSRF token:
    - Clears user_id from session
    - Redirects to login
    """
    # Create and login student
    with app.app_context():
        student = User(name="Daisy", email="daisy@example.com", role="student")
        student.set_password("Password123")
        db.session.add(student)
        db.session.commit()

    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    client.post("/auth/login", data={
        "csrf_token": token,
        "email": "daisy@example.com",
        "password": "Password123"
    })

    # Get page with navbar to extract logout form CSRF token
    res = client.get("/interview/start")
    token = extract_csrf_token(res)

    # POST to /auth/logout
    res_logout = client.post("/auth/logout", data={"csrf_token": token})
    assert res_logout.status_code == 302
    assert "/auth/login" in res_logout.headers["Location"]

    # Session user_id must be cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_student_blocked_from_admin_page(client, app):
    """
    Test that a logged-in student cannot access /admin/ (returns 403 Forbidden).
    """
    with app.app_context():
        student = User(name="Eve", email="eve@example.com", role="student")
        student.set_password("Password123")
        db.session.add(student)
        db.session.commit()

    # Log in as student
    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    client.post("/auth/login", data={
        "csrf_token": token,
        "email": "eve@example.com",
        "password": "Password123"
    })

    # Try accessing admin panel (must return 403 Forbidden)
    res_admin = client.get("/admin/")
    assert res_admin.status_code == 403
    assert "Access Denied" in res_admin.get_data(as_text=True)


def test_admin_allowed_on_admin_page(client, app):
    """
    Test that a logged-in admin can access /admin/ successfully (status 200).
    """
    with app.app_context():
        admin = User(name="Frank Admin", email="frank@college.edu", role="admin")
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()

    # Log in as admin
    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    client.post("/auth/login", data={
        "csrf_token": token,
        "email": "frank@college.edu",
        "password": "AdminPass123"
    })

    # Access admin panel
    res_admin = client.get("/admin/")
    assert res_admin.status_code == 200
    assert "Placement Officer / Admin Dashboard" in res_admin.get_data(as_text=True)
