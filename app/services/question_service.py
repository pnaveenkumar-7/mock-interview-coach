import random
from sqlalchemy import func
from app.models import Question


def pick_questions(
    interview_type,
    count,
    exclude_ids=None,
    target_dimension=None,
    difficulty=None
):
    """
    Selects up to `count` unique random questions for an interview session.

    Parameters:
    - interview_type (str): 'HR', 'technical', or 'behavioral' (case-insensitive)
    - count (int): Desired number of questions (returns available if fewer exist)
    - exclude_ids (iterable, optional): IDs of questions to exclude (prevents repeats)
    - target_dimension (str, optional): Preferred rubric dimension tag
    - difficulty (str, optional): Preferred difficulty level ('easy', 'medium', 'hard')

    Returns:
    - list[Question]: Unique Question objects (no duplicates within the returned list)
    """
    if count <= 0:
        return []

    exclude_set = set(exclude_ids or [])

    # Base query: filter by interview type (case-insensitive)
    query = Question.query.filter(func.lower(Question.type) == interview_type.strip().lower())

    # Exclude previously asked question IDs
    if exclude_set:
        query = query.filter(~Question.id.in_(exclude_set))

    # Apply difficulty filter if specified
    if difficulty:
        query = query.filter(func.lower(Question.difficulty) == difficulty.strip().lower())

    # Fetch all matching candidate questions
    candidates = query.all()

    if not candidates:
        return []

    # If available candidates are fewer than or equal to requested count, return all shuffled
    if len(candidates) <= count:
        random.shuffle(candidates)
        return candidates

    # If a target dimension is requested, prioritize questions matching that dimension
    if target_dimension:
        norm_target = target_dimension.strip().lower()
        preferred = [q for q in candidates if q.dimension_tag.lower() == norm_target]
        others = [q for q in candidates if q.dimension_tag.lower() != norm_target]

        random.shuffle(preferred)
        random.shuffle(others)

        # Pick as many matching target dimension questions as needed, then backfill
        selected = preferred[:count]
        if len(selected) < count:
            remaining_slots = count - len(selected)
            selected.extend(others[:remaining_slots])

        return selected

    # Default: randomly sample without replacement
    return random.sample(candidates, count)

