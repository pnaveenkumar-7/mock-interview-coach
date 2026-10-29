import json
import pytest
from app.extensions import db
from app.models import Question
from app.services.question_service import pick_questions
from seed_questions import seed_questions, validate_question_data


@pytest.fixture
def seeded_app(app):
    """
    Seeds the in-memory test database with data/questions.json for question service tests.
    """
    with app.app_context():
        seed_questions(json_path="data/questions.json", app=app)
    return app


def test_pick_questions_no_duplicates_in_single_call(seeded_app):
    """
    Verify that one pick_questions call never returns the same question twice.
    """
    with seeded_app.app_context():
        questions = pick_questions("technical", count=15)
        assert len(questions) == 15
        ids = [q.id for q in questions]
        assert len(ids) == len(set(ids)), "Returned questions must be strictly unique"


def test_pick_questions_respects_exclude_ids(seeded_app):
    """
    Verify that question IDs passed in exclude_ids are never returned.
    """
    with seeded_app.app_context():
        # Pick 5 initial questions
        first_batch = pick_questions("HR", count=5)
        exclude_ids = [q.id for q in first_batch]

        # Pick next 5 questions excluding the first batch
        second_batch = pick_questions("HR", count=5, exclude_ids=exclude_ids)
        second_batch_ids = [q.id for q in second_batch]

        # Ensure no overlap between batches
        assert len(set(exclude_ids).intersection(set(second_batch_ids))) == 0


def test_pick_questions_target_dimension_preference(seeded_app):
    """
    Verify that questions matching target_dimension are prioritized.
    """
    with seeded_app.app_context():
        target = "technical_accuracy"
        # Total technical_accuracy in technical bank is 12
        picked = pick_questions("technical", count=8, target_dimension=target)
        assert len(picked) == 8

        # All 8 should match the target dimension because at least 12 are available
        for q in picked:
            assert q.dimension_tag == target


def test_pick_questions_count_and_exhaustion(seeded_app):
    """
    Verify count is respected, and when more are requested than available,
    returns all available without duplicates or errors.
    """
    with seeded_app.app_context():
        # Standard count
        picked = pick_questions("behavioral", count=7)
        assert len(picked) == 7

        # Total behavioral questions in bank is 30. Requesting 100 should return all 30.
        over_requested = pick_questions("behavioral", count=100)
        assert len(over_requested) == 30
        ids = [q.id for q in over_requested]
        assert len(ids) == len(set(ids))


def test_seeding_idempotence(app):
    """
    Verify that running seed_questions twice does not create duplicate entries.
    """
    with app.app_context():
        # First seeding run
        stats1 = seed_questions(json_path="data/questions.json", app=app)
        assert stats1["added"]["HR"] == 30
        assert stats1["added"]["behavioral"] == 30
        assert stats1["added"]["technical"] == 60
        assert stats1["skipped"] == 0

        initial_count = Question.query.count()
        assert initial_count == 120

        # Second seeding run (all should be skipped)
        stats2 = seed_questions(json_path="data/questions.json", app=app)
        assert stats2["added"]["HR"] == 0
        assert stats2["added"]["behavioral"] == 0
        assert stats2["added"]["technical"] == 0
        assert stats2["skipped"] == 120

        # Database count must remain unchanged
        assert Question.query.count() == 120


def test_seed_rejects_invalid_entry(tmp_path, app):
    """
    Verify that seed_questions validates every entry and refuses to insert anything
    if any entry contains invalid fields (type, difficulty, dimension_tag, or empty text).
    """
    invalid_data = [
        {
            "text": "Valid question one?",
            "type": "technical",
            "difficulty": "easy",
            "dimension_tag": "clarity",
            "ideal_points": "Point 1\nPoint 2"
        },
        {
            "text": "Invalid question with wrong type?",
            "type": "nonexistent_type",  # Invalid type
            "difficulty": "easy",
            "dimension_tag": "relevance",
            "ideal_points": "Point 1"
        }
    ]

    invalid_file = tmp_path / "invalid_questions.json"
    invalid_file.write_text(json.dumps(invalid_data), encoding="utf-8")

    with app.app_context():
        initial_count = Question.query.count()
        res = seed_questions(json_path=str(invalid_file), app=app)

        # Must return None indicating rejection
        assert res is None

        # Verify nothing was inserted (transaction not touched)
        assert Question.query.count() == initial_count


def test_validation_function_rules():
    """
    Unit test validation checks for text, difficulty, and dimension_tag.
    """
    # Empty text
    is_valid, msg = validate_question_data([{"text": "", "type": "HR", "difficulty": "easy", "dimension_tag": "relevance"}])
    assert is_valid is False
    assert "empty or invalid 'text'" in msg

    # Invalid difficulty
    is_valid, msg = validate_question_data([{"text": "Sample", "type": "HR", "difficulty": "impossible", "dimension_tag": "relevance"}])
    assert is_valid is False
    assert "invalid difficulty" in msg

    # Invalid dimension tag
    is_valid, msg = validate_question_data([{"text": "Sample", "type": "HR", "difficulty": "easy", "dimension_tag": "magic"}])
    assert is_valid is False
    assert "invalid dimension_tag" in msg

