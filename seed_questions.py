import os
import sys
import json
from app import create_app
from app.extensions import db
from app.models import Question

# Validation constraints
VALID_TYPES = {"HR", "technical", "behavioral"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_DIMENSIONS = {
    "relevance",
    "clarity",
    "completeness",
    "technical_accuracy",
    "communication"
}


def validate_question_data(data):
    """
    Validates every entry in the dataset.
    Returns (True, None) if all are valid, or (False, error_message).
    """
    if not isinstance(data, list) or len(data) == 0:
        return False, "Data must be a non-empty list of question objects."

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            return False, f"Entry #{idx} is not a valid JSON object."

        text = item.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            return False, f"Entry #{idx} has an empty or invalid 'text' field."

        q_type = item.get("type")
        if q_type not in VALID_TYPES:
            return False, (
                f"Entry #{idx} ('{text[:40]}...') has invalid type '{q_type}'. "
                f"Must be one of {sorted(VALID_TYPES)}."
            )

        difficulty = item.get("difficulty")
        if difficulty not in VALID_DIFFICULTIES:
            return False, (
                f"Entry #{idx} ('{text[:40]}...') has invalid difficulty '{difficulty}'. "
                f"Must be one of {sorted(VALID_DIFFICULTIES)}."
            )

        dimension_tag = item.get("dimension_tag")
        if dimension_tag not in VALID_DIMENSIONS:
            return False, (
                f"Entry #{idx} ('{text[:40]}...') has invalid dimension_tag '{dimension_tag}'. "
                f"Must be one of {sorted(VALID_DIMENSIONS)}."
            )

    return True, None


def seed_questions(json_path="data/questions.json", app=None):
    """
    Reads questions from a JSON file, validates all entries,
    and inserts non-duplicate questions into the database.
    
    Safe to run multiple times: skips questions whose text already exists.
    """
    if not os.path.exists(json_path):
        print(f"[ERROR] Question file not found: {json_path}")
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON from {json_path}: {e}")
        return None

    # Strict pre-validation: All entries must be valid before touching the database
    is_valid, error_msg = validate_question_data(questions_data)
    if not is_valid:
        print(f"[VALIDATION ERROR] Seeding aborted: {error_msg}")
        return None

    if app is None:
        app = create_app()

    stats = {
        "added": {"HR": 0, "technical": 0, "behavioral": 0},
        "skipped": 0,
        "total_in_file": len(questions_data)
    }

    with app.app_context():
        # Query existing question texts for fast idempotency check
        existing_texts = {q.text.strip().lower() for q in Question.query.with_entities(Question.text).all()}

        for item in questions_data:
            normalized_text = item["text"].strip().lower()

            if normalized_text in existing_texts:
                stats["skipped"] += 1
                continue

            # Format ideal_points as plain text with one point per line
            ideal_points = item.get("ideal_points")
            if isinstance(ideal_points, list):
                ideal_points = "\n".join(str(p).strip() for p in ideal_points)
            elif isinstance(ideal_points, str):
                ideal_points = ideal_points.strip()
            else:
                ideal_points = None

            question = Question(
                text=item["text"].strip(),
                type=item["type"].strip(),
                difficulty=item["difficulty"].strip(),
                dimension_tag=item["dimension_tag"].strip(),
                ideal_points=ideal_points,
                source=item.get("source", "bank").strip()
            )

            db.session.add(question)
            existing_texts.add(normalized_text)
            stats["added"][item["type"]] += 1

        db.session.commit()

    print("[SUCCESS] Question seeding completed:")
    print(f" - HR Questions Added:         {stats['added']['HR']}")
    print(f" - Technical Questions Added:  {stats['added']['technical']}")
    print(f" - Behavioral Questions Added: {stats['added']['behavioral']}")
    print(f" - Skipped (Already Exist):    {stats['skipped']}")
    print(f" - Total Processed:            {stats['total_in_file']}")

    return stats


if __name__ == "__main__":
    result = seed_questions()
    if result is None:
        sys.exit(1)

