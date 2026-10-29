from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, g
from app.extensions import db
from app.models import InterviewSession, Question, Answer, utc_now
from app.auth_utils import login_required, validate_csrf
from app.services.question_service import pick_questions

# Create Blueprint for interview sessions
interview_bp = Blueprint("interview", __name__, url_prefix="/interview")

VALID_TYPES = {"hr": "HR", "technical": "technical", "behavioral": "behavioral"}


@interview_bp.route("/start", methods=["GET", "POST"])
@login_required
def start_interview():
    """
    Start Interview page.
    Validates interview configuration, creates an InterviewSession,
    picks questions via question_service, and redirects to the live session.
    """
    if request.method == "POST":
        validate_csrf()

        raw_type = request.form.get("interview_type", "").strip().lower()
        raw_count = request.form.get("num_questions", "").strip()

        # Validate interview type
        if raw_type not in VALID_TYPES:
            flash("Invalid interview type selected.", "danger")
            return render_template("interview/start.html", selected_type="technical", selected_num=5)

        normalized_type = VALID_TYPES[raw_type]

        # Validate question count (3 to 10)
        try:
            num_questions = int(raw_count)
            if num_questions < 3 or num_questions > 10:
                raise ValueError()
        except ValueError:
            flash("Number of questions must be between 3 and 10.", "danger")
            return render_template("interview/start.html", selected_type=raw_type, selected_num=5)

        # Pick random questions from the question bank
        picked = pick_questions(interview_type=normalized_type, count=num_questions)
        if not picked:
            flash("No questions found for the selected category. Please seed the question bank.", "danger")
            return render_template("interview/start.html", selected_type=raw_type, selected_num=num_questions)

        # Create new interview session
        interview_session = InterviewSession(
            user_id=g.current_user.id,
            interview_type=normalized_type,
            mode="fixed",
            started_at=utc_now()
        )
        interview_session.set_question_ids([q.id for q in picked])

        db.session.add(interview_session)
        db.session.commit()

        return redirect(url_for("interview.session_view", session_id=interview_session.id))

    return render_template("interview/start.html", selected_type="technical", selected_num=5)


@interview_bp.route("/session/<int:session_id>", methods=["GET", "POST"])
@login_required
def session_view(session_id):
    """
    Live interview session view.
    Renders one question at a time and handles answer submission.
    Server strictly controls question progression based on saved answers count.
    """
    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        abort(404, description="Interview session not found.")

    # Access control: only owner can open their interview session
    if interview_session.user_id != g.current_user.id:
        abort(403, description="Access forbidden: you do not own this interview session.")

    q_ids = interview_session.get_question_ids()
    total_questions = len(q_ids)
    answered_count = len(interview_session.answers)

    # If session is already finished, redirect to report
    if interview_session.ended_at is not None or answered_count >= total_questions:
        if not interview_session.ended_at:
            interview_session.ended_at = utc_now()
            db.session.commit()
        return redirect(url_for("interview.report_view", session_id=session_id))

    current_q_id = q_ids[answered_count]
    current_question = db.session.get(Question, current_q_id)

    if request.method == "POST":
        validate_csrf()

        # Guard against out-of-order or duplicate submissions
        submitted_q_id = request.form.get("question_id", type=int)
        if submitted_q_id is not None and submitted_q_id != current_q_id:
            # Client submitted an answer for an old or invalid question: ignore and refresh
            return redirect(url_for("interview.session_view", session_id=session_id))

        # Check for duplicate submission directly
        existing_answer = Answer.query.filter_by(
            session_id=session_id,
            question_id=current_q_id
        ).first()

        if existing_answer:
            # Duplicate submission detected: ignore and reload current state
            return redirect(url_for("interview.session_view", session_id=session_id))

        transcript = request.form.get("transcript", "").strip()

        # Reject empty answers
        if not transcript:
            flash("Answer cannot be empty. Please type your response before submitting.", "danger")
            return render_template(
                "interview/session.html",
                session=interview_session,
                question=current_question,
                current_number=answered_count + 1,
                total_questions=total_questions
            )

        # Reject answers exceeding 3000 characters
        if len(transcript) > 3000:
            flash("Your answer exceeds the 3000 character limit. Please shorten your response.", "danger")
            return render_template(
                "interview/session.html",
                session=interview_session,
                question=current_question,
                current_number=answered_count + 1,
                total_questions=total_questions,
                transcript=transcript
            )

        # Save student's typed answer
        now = utc_now()
        answer = Answer(
            session_id=session_id,
            question_id=current_q_id,
            transcript=transcript,
            input_method="typed",
            started_at=now,
            ended_at=now
        )
        db.session.add(answer)

        # Check if this was the last question in the session
        if answered_count + 1 >= total_questions:
            interview_session.ended_at = now
            db.session.commit()
            flash("Interview complete! Here is your session summary.", "success")
            return redirect(url_for("interview.report_view", session_id=session_id))

        db.session.commit()
        return redirect(url_for("interview.session_view", session_id=session_id))

    return render_template(
        "interview/session.html",
        session=interview_session,
        question=current_question,
        current_number=answered_count + 1,
        total_questions=total_questions
    )


@interview_bp.route("/report/<int:session_id>")
@login_required
def report_view(session_id):
    """
    Interview completion report placeholder.
    Opening an unfinished session redirects back to /interview/session/<id>.
    """
    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        abort(404, description="Interview session not found.")

    # Access control: only owner can view their session report
    if interview_session.user_id != g.current_user.id:
        abort(403, description="Access forbidden: you do not own this report.")

    q_ids = interview_session.get_question_ids()
    total_questions = len(q_ids)

    # Opening report for an unfinished session redirects back to the live session
    if interview_session.ended_at is None and len(interview_session.answers) < total_questions:
        flash("This interview session is still in progress. Please complete all questions.", "info")
        return redirect(url_for("interview.session_view", session_id=session_id))

    return render_template(
        "interview/report.html",
        session=interview_session,
        answers=interview_session.answers,
        total_questions=total_questions
    )


@interview_bp.route("/")
@login_required
def interview_index():
    """
    Default interview route redirects to the setup page.
    """
    return redirect(url_for("interview.start_interview"))
