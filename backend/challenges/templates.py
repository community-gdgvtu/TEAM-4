"""Allowlisted challenge templates. Hidden tests never enter API challenge objects."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TEMPLATES: dict[str, dict[str, Any]] = {
    "python-normalize-records-v1": {
        "template_id": "python-normalize-records-v1",
        "version": "1.0",
        "skill": "Python",
        "challenge_type": "PYTHON_FUNCTION",
        "level": "INTERMEDIATE",
        "title": "Normalize imported contributor records",
        "rationale": "The repository contains substantive Python and tests. The remaining uncertainty is careful edge-case handling.",
        "instructions": "Implement normalize_records(records). Ignore rows without a usable email, normalize email case and surrounding whitespace, keep the first name for each email, and return dictionaries sorted by email. Do not mutate the input.",
        "starter_code": "def normalize_records(records):\n    # Return [{'email': ..., 'name': ...}, ...]\n    pass\n",
        "concept_questions": [
            {"id": "py-q1", "prompt": "Why avoid mutating the input list?", "options": ["It preserves caller-owned state", "It makes sorting impossible", "It disables exceptions"], "correct": 0},
            {"id": "py-q2", "prompt": "Which comparison is appropriate for normalized email keys?", "options": ["Object identity", "Lower-cased trimmed text", "String length only"], "correct": 1}
        ],
        "public_tests": [
            {"name": "normalizes-email", "description": "Email case and surrounding whitespace are normalized."},
            {"name": "deduplicates", "description": "The first record for a normalized email is retained."},
            {"name": "stable-order", "description": "Results are sorted by normalized email."}
        ],
        "demo_solution": "def normalize_records(records):\n    by_email = {}\n    for record in records:\n        email = str(record.get('email', '')).strip().lower()\n        if not email or '@' not in email:\n            continue\n        if email not in by_email:\n            by_email[email] = {'email': email, 'name': str(record.get('name', '')).strip()}\n    return [by_email[email] for email in sorted(by_email)]\n",
    },
    "fastapi-duplicate-email-v1": {
        "template_id": "fastapi-duplicate-email-v1",
        "version": "1.0",
        "skill": "FastAPI",
        "challenge_type": "FASTAPI_VALIDATION",
        "level": "INTERMEDIATE",
        "title": "Reject duplicate emails without breaking user creation",
        "rationale": "The evidence shows a typed FastAPI creation route and a normal-path API test, but duplicate conflict handling is absent.",
        "instructions": "Implement create_user(payload, users). Treat email addresses case-insensitively. New users must be stored and return {'status_code': 201, 'body': user}. A duplicate must preserve existing data and return {'status_code': 409, 'body': {'detail': 'Email already exists'}}.",
        "starter_code": "def create_user(payload, users):\n    # users is a dictionary keyed by normalized email\n    pass\n",
        "concept_questions": [
            {"id": "api-q1", "prompt": "Which HTTP status best represents a duplicate-email conflict?", "options": ["201", "409", "500"], "correct": 1},
            {"id": "api-q2", "prompt": "Why normalize email before lookup?", "options": ["To make JSON smaller", "To prevent case variants bypassing uniqueness", "To skip validation"], "correct": 1}
        ],
        "public_tests": [
            {"name": "creation-preserved", "description": "A valid new user still returns HTTP 201 and is stored."},
            {"name": "duplicate-conflict", "description": "A duplicate returns HTTP 409 with a safe detail."},
            {"name": "case-insensitive", "description": "Email uniqueness is case-insensitive."},
            {"name": "no-regression", "description": "Rejected duplicates do not overwrite stored user data."}
        ],
        "demo_solution": "def create_user(payload, users):\n    email = str(payload.get('email', '')).strip().lower()\n    if email in users:\n        return {'status_code': 409, 'body': {'detail': 'Email already exists'}}\n    user = {'name': str(payload.get('name', '')).strip(), 'email': email}\n    users[email] = user\n    return {'status_code': 201, 'body': user}\n",
    },
    "sql-customer-orders-v1": {
        "template_id": "sql-customer-orders-v1",
        "version": "1.0",
        "skill": "SQL",
        "challenge_type": "SQL_QUERY",
        "level": "INTERMEDIATE",
        "title": "Report users and their event count",
        "rationale": "The evidence includes relational schema and reporting SQL. The remaining uncertainty is correct outer joins and aggregation.",
        "instructions": "Write one read-only SQLite SELECT query returning name and event_count for every user, including users with zero registrations. Sort by event_count descending, then name ascending.",
        "starter_code": "SELECT\n    -- name, event_count\nFROM users;\n",
        "concept_questions": [
            {"id": "sql-q1", "prompt": "Which join preserves users with no registrations?", "options": ["INNER JOIN", "LEFT JOIN", "CROSS JOIN"], "correct": 1},
            {"id": "sql-q2", "prompt": "What should be grouped to produce one row per user?", "options": ["User identity", "Only the event title", "Nothing"], "correct": 0}
        ],
        "public_tests": [
            {"name": "all-users", "description": "Users without registrations remain in the result."},
            {"name": "correct-counts", "description": "Registration counts are correct."},
            {"name": "deterministic-order", "description": "Rows use the requested deterministic ordering."}
        ],
        "demo_solution": "SELECT u.name, COUNT(r.event_id) AS event_count\nFROM users AS u\nLEFT JOIN registrations AS r ON r.user_id = u.id\nGROUP BY u.id, u.name\nORDER BY event_count DESC, u.name ASC;",
    },
}


def get_template(template_id: str) -> dict[str, Any]:
    try:
        return deepcopy(TEMPLATES[template_id])
    except KeyError as exc:
        raise KeyError("Unsupported challenge template") from exc


def template_for_skill(skill: str) -> dict[str, Any] | None:
    return next((deepcopy(value) for value in TEMPLATES.values() if value["skill"] == skill), None)


def public_template(template: dict[str, Any], include_demo_solution: bool = False) -> dict[str, Any]:
    value = {key: deepcopy(item) for key, item in template.items() if key not in {"demo_solution"}}
    value["concept_questions"] = [
        {key: item for key, item in question.items() if key != "correct"}
        for question in template.get("concept_questions", [])
    ]
    if include_demo_solution:
        value["demo_solution"] = template.get("demo_solution")
    return value


def score_concepts(template: dict[str, Any], answers: dict[str, int]) -> tuple[int, int]:
    questions = template.get("concept_questions", [])
    correct = sum(answers.get(question["id"]) == question["correct"] for question in questions)
    return correct, len(questions)

