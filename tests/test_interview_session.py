import re
import pytest
from app.extensions import db
from app.models import User, InterviewSession, Question, Answer
from seed_questions import seed_questions


def extract_csrf_token(response):
    """Helper to extract CSRF token from HTML response."""
    html = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', html)
    assert match is not None, "CSRF token not found in response HTML"
    return match.group(1)


@pytest.fixture
def seeded_db(app):
    """Seed question bank in test database."""
    with app.app_context():
        seed_questions(json_path="data/questions.json", app=app)
    return app


def create_and_login_user(client, app, name="Student User", email="student@test.com", role="student"):
    """Helper to register and log in a user."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, role=role)
            user.set_password("Password123")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    # Clear any previous session so client can log in fresh
    with client.session_transaction() as sess:
        sess.clear()

    res = client.get("/auth/login")
    token = extract_csrf_token(res)
    client.post("/auth/login", data={
        "csrf_token": token,
        "email": email,
        "password": "Password123"
    })
    return user_id


def test_start_session_validation_and_creation(client, seeded_db):
    """
    Test creating a session via POST /interview/start:
    - Validates type and count (3-10)
    - Creates InterviewSession and picks questions
    - Redirects to /interview/session/<id>
    """
    user_id = create_and_login_user(client, seeded_db)

    res = client.get("/interview/start")
    token = extract_csrf_token(res)

    # 1. Test invalid count (< 3)
    res_invalid_count = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "2"
    })
    assert "Number of questions must be between 3 and 10." in res_invalid_count.get_data(as_text=True)

    # 2. Test invalid count (> 10)
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_high_count = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "15"
    })
    assert "Number of questions must be between 3 and 10." in res_high_count.get_data(as_text=True)

    # 3. Test invalid type
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_invalid_type = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "invalid_type",
        "num_questions": "5"
    })
    assert "Invalid interview type selected." in res_invalid_type.get_data(as_text=True)

    # 4. Valid start request
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_valid = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "4"
    })

    assert res_valid.status_code == 302
    assert "/interview/session/" in res_valid.headers["Location"]

    session_id = int(res_valid.headers["Location"].split("/")[-1])

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        assert session_obj is not None
        assert session_obj.user_id == user_id
        assert session_obj.interview_type == "technical"
        assert session_obj.mode == "fixed"
        q_ids = session_obj.get_question_ids()
        assert len(q_ids) == 4


def test_question_progression_and_answer_submission(client, seeded_db):
    """
    Test live interview progression:
    - Server dictates question order based on answered count
    - Submitting answer increments progress (1 of 3 -> 2 of 3 -> 3 of 3)
    - Submitting final answer finishes session and redirects to report
    """
    user_id = create_and_login_user(client, seeded_db)

    # Start 3-question interview
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "HR",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        q_ids = session_obj.get_question_ids()
        q1 = db.session.get(Question, q_ids[0])
        q2 = db.session.get(Question, q_ids[1])
        q3 = db.session.get(Question, q_ids[2])

    # Question 1: Check display
    res_q1 = client.get(f"/interview/session/{session_id}")
    assert res_q1.status_code == 200
    assert "Question 1 of 3" in res_q1.get_data(as_text=True)
    assert q1.text in res_q1.get_data(as_text=True)

    # Submit Answer 1
    token = extract_csrf_token(res_q1)
    res_ans1 = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "This is my detailed response to question one."
    })
    assert res_ans1.status_code == 302
    assert f"/interview/session/{session_id}" in res_ans1.headers["Location"]

    # Question 2: Check display
    res_q2 = client.get(f"/interview/session/{session_id}")
    assert "Question 2 of 3" in res_q2.get_data(as_text=True)
    assert q2.text in res_q2.get_data(as_text=True)

    # Submit Answer 2
    token = extract_csrf_token(res_q2)
    res_ans2 = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Here is my answer to question two explaining my past experience."
    })
    assert res_ans2.status_code == 302

    # Question 3: Check display
    res_q3 = client.get(f"/interview/session/{session_id}")
    assert "Question 3 of 3" in res_q3.get_data(as_text=True)
    assert q3.text in res_q3.get_data(as_text=True)

    # Submit Answer 3 (Final Question) -> redirects to report
    token = extract_csrf_token(res_q3)
    res_ans3 = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Final answer for question three."
    })
    assert res_ans3.status_code == 302
    assert f"/interview/report/{session_id}" in res_ans3.headers["Location"]

    # Verify database state
    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        assert session_obj.ended_at is not None
        assert len(session_obj.answers) == 3

        # Verify answer attributes
        ans = session_obj.answers[0]
        assert ans.input_method == "typed"
        assert ans.transcript == "This is my detailed response to question one."
        assert ans.started_at is not None
        assert ans.ended_at is not None


def test_reject_empty_and_long_answers(client, seeded_db):
    """
    Verify rejection of empty answers and answers over 3000 characters.
    """
    create_and_login_user(client, seeded_db)

    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    # 1. Empty answer
    res_page = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_page)
    res_empty = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "   "
    })
    assert "Answer cannot be empty." in res_empty.get_data(as_text=True)

    # 2. Answer exceeding 3000 characters
    long_text = "A" * 3005
    res_long = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": long_text
    })
    assert "exceeds the 3000 character limit" in res_long.get_data(as_text=True)

    # Verify no answers were saved
    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        assert len(session_obj.answers) == 0


def test_session_access_control_between_users(client, seeded_db):
    """
    Verify that User B cannot view or submit answers to User A's session (returns 403).
    """
    # 1. User A creates session
    user_a_id = create_and_login_user(client, seeded_db, name="User A", email="usera@test.com")
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    # 2. User B logs in
    user_b_id = create_and_login_user(client, seeded_db, name="User B", email="userb@test.com")
    assert user_a_id != user_b_id

    # User B attempts to access User A's session
    res_b_session = client.get(f"/interview/session/{session_id}")
    assert res_b_session.status_code == 403

    # User B attempts to view User A's report
    res_b_report = client.get(f"/interview/report/{session_id}")
    assert res_b_report.status_code == 403


def test_nonexistent_session_returns_404(client, seeded_db):
    """
    Verify that accessing a non-existent session ID returns 404.
    """
    create_and_login_user(client, seeded_db)

    res_session = client.get("/interview/session/999999")
    assert res_session.status_code == 404

    res_report = client.get("/interview/report/999999")
    assert res_report.status_code == 404


def test_report_redirects_if_session_unfinished(client, seeded_db):
    """
    Verify that opening /interview/report/<id> before all questions are answered
    redirects back to /interview/session/<id>.
    """
    create_and_login_user(client, seeded_db)

    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "behavioral",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    # Attempt to access report prematurely
    res_report = client.get(f"/interview/report/{session_id}")
    assert res_report.status_code == 302
    assert f"/interview/session/{session_id}" in res_report.headers["Location"]


def test_finished_session_redirects_to_report(client, seeded_db):
    """
    Verify that opening /interview/session/<id> after completion redirects to /interview/report/<id>.
    """
    create_and_login_user(client, seeded_db)

    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "HR",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    # Answer all 3 questions
    for i in range(3):
        res_page = client.get(f"/interview/session/{session_id}")
        token = extract_csrf_token(res_page)
        client.post(f"/interview/session/{session_id}", data={
            "csrf_token": token,
            "transcript": f"Answer for question {i + 1}"
        })

    # Accessing /session/<id> now should redirect to /report/<id>
    res_access_finished = client.get(f"/interview/session/{session_id}")
    assert res_access_finished.status_code == 302
    assert f"/interview/report/{session_id}" in res_access_finished.headers["Location"]


def test_duplicate_submit_ignored(client, seeded_db):
    """
    Verify that duplicate submits for the same question are ignored
    and do not violate database unique constraints or duplicate answers.
    """
    create_and_login_user(client, seeded_db)

    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        q_ids = session_obj.get_question_ids()

    # First submit
    res_page = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_page)
    res_post1 = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "question_id": q_ids[0],
        "transcript": "First submission text"
    })
    assert res_post1.status_code == 302

    # Attempt to post again using the old token/form for the same question
    res_post_duplicate = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "question_id": q_ids[0],
        "transcript": "Duplicate submission text"
    })
    assert res_post_duplicate.status_code == 302

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        # Should only have 1 answer recorded
        assert len(session_obj.answers) == 1
        assert session_obj.answers[0].transcript == "First submission text"
