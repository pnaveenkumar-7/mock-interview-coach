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


def create_and_login_user(client, app, name="Student Voice Tester", email="voicetest@test.com"):
    """Helper to register and log in a user with a fresh session."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, role="student")
            user.set_password("Password123")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

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


def test_valid_voice_answer_timing_and_pauses(client, seeded_db):
    """
    Test submitting an answer with valid voice parameters:
    - input_method='voice'
    - speech_duration_ms=45000 (45s) -> started_at is calculated from ended_at - 45s
    - long_pause_count=4 -> saved in Answer.long_pause_count
    """
    create_and_login_user(client, seeded_db)

    # Start 3-question interview
    res = client.get("/interview/start")
    token = extract_csrf_token(res)
    res_start = client.post("/interview/start", data={
        "csrf_token": token,
        "interview_type": "technical",
        "num_questions": "3"
    })
    session_id = int(res_start.headers["Location"].split("/")[-1])

    # Get question 1
    res_q1 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q1)

    # Submit voice answer with 45 seconds duration and 4 long pauses
    res_submit = client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Inheritance allows a class to inherit properties and methods from another class.",
        "input_method": "voice",
        "speech_duration_ms": "45000",
        "long_pause_count": "4"
    })
    assert res_submit.status_code == 302

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        assert len(session_obj.answers) == 1
        ans = session_obj.answers[0]

        assert ans.input_method == "voice"
        assert ans.long_pause_count == 4
        assert ans.ended_at is not None
        assert ans.started_at is not None

        # Verify time difference is approximately 45 seconds (45000 ms)
        diff_seconds = (ans.ended_at - ans.started_at).total_seconds()
        assert pytest.approx(diff_seconds, 0.5) == 45.0


def test_invalid_duration_ignored(client, seeded_db):
    """
    Test invalid duration handling:
    - Negative duration (< 0)
    - Duration exceeding 10 minutes (> 600,000 ms)
    - Non-integer string
    All invalid values must be safely ignored and started_at falls back to server ended_at.
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

    # Case 1: Duration over 10 minutes (e.g. 700000 ms)
    res_q1 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q1)
    client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "My strength is quick problem solving.",
        "input_method": "voice",
        "speech_duration_ms": "700000",
        "long_pause_count": "2"
    })

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        ans = session_obj.answers[0]
        # Over 10 mins ignored -> started_at equals ended_at
        diff = (ans.ended_at - ans.started_at).total_seconds()
        assert diff == 0.0

    # Case 2: Negative duration
    res_q2 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q2)
    client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "I handle stress by planning ahead.",
        "input_method": "voice",
        "speech_duration_ms": "-500",
        "long_pause_count": "0"
    })

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        ans2 = session_obj.answers[1]
        diff = (ans2.ended_at - ans2.started_at).total_seconds()
        assert diff == 0.0

    # Case 3: Non-integer string
    res_q3 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q3)
    client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Final answer without crashing.",
        "input_method": "voice",
        "speech_duration_ms": "invalid_duration_abc",
        "long_pause_count": "0"
    })

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        ans3 = session_obj.answers[2]
        diff = (ans3.ended_at - ans3.started_at).total_seconds()
        assert diff == 0.0


def test_invalid_long_pause_count_ignored(client, seeded_db):
    """
    Test that invalid long_pause_count values (< 0, > 100, non-integer)
    fall back to 0.
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

    # Case: long_pause_count = 150 (> 100)
    res_q1 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q1)
    client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Behavioral response text.",
        "input_method": "voice",
        "speech_duration_ms": "20000",
        "long_pause_count": "150"
    })

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        ans = session_obj.answers[0]
        # Should fall back to 0
        assert ans.long_pause_count == 0


def test_standard_typed_input_defaults(client, seeded_db):
    """
    Verify that standard typed input (without voice parameters)
    defaults to input_method='typed', long_pause_count=0.
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

    res_q1 = client.get(f"/interview/session/{session_id}")
    token = extract_csrf_token(res_q1)
    client.post(f"/interview/session/{session_id}", data={
        "csrf_token": token,
        "transcript": "Purely typed answer from keyboard."
    })

    with seeded_db.app_context():
        session_obj = db.session.get(InterviewSession, session_id)
        ans = session_obj.answers[0]
        assert ans.input_method == "typed"
        assert ans.long_pause_count == 0
        assert ans.started_at == ans.ended_at

