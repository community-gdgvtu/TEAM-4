from __future__ import annotations

import pytest

from backend.challenges.runner import verify_submission
from backend.challenges.templates import get_template, score_concepts


@pytest.mark.parametrize(
    "template_id",
    [
        "python-normalize-records-v1",
        "fastapi-duplicate-email-v1",
        "sql-customer-orders-v1",
    ],
)
def test_bundled_python_fastapi_and_sql_solutions_pass(template_id: str):
    template = get_template(template_id)

    result = verify_submission(template_id, template["demo_solution"])

    assert result["passed"] is True
    assert result["tests_total"] > 0
    assert result["tests_passed"] == result["tests_total"]
    assert all(item["passed"] for item in result["test_results"])


@pytest.mark.parametrize(
    ("template_id", "solution"),
    [
        (
            "python-normalize-records-v1",
            "def normalize_records(records):\n    return records\n",
        ),
        (
            "fastapi-duplicate-email-v1",
            "def create_user(payload, users):\n    return {'status_code': 201, 'body': payload}\n",
        ),
        ("sql-customer-orders-v1", "SELECT name, 0 AS event_count FROM users"),
    ],
)
def test_wrong_solutions_fail_without_claiming_all_tests_passed(
    template_id: str, solution: str
):
    result = verify_submission(template_id, solution)

    assert result["passed"] is False
    assert result["tests_passed"] < result["tests_total"]


def test_perfect_concept_answers_do_not_execute_or_verify_live_proof():
    template = get_template("fastapi-duplicate-email-v1")
    answers = {
        question["id"]: question["correct"]
        for question in template["concept_questions"]
    }

    correct, total = score_concepts(template, answers)

    assert correct == total
    # Concept scoring returns context only; it has no pass flag or event side effect.
    assert "passed" not in template
    assert "verification_event_id" not in template


@pytest.mark.parametrize(
    ("solution", "expected_error"),
    [
        ("def normalize_records(:\n    pass\n", "invalid Python syntax"),
        (
            "import os\ndef normalize_records(records):\n    return []\n",
            "Import is not allowed",
        ),
        (
            "def normalize_records(records):\n    return open('/etc/passwd').read()\n",
            "Use of open is not allowed",
        ),
        (
            "value = 1\ndef normalize_records(records):\n    return []\n",
            "Only the required function definition is allowed",
        ),
    ],
)
def test_python_syntax_and_forbidden_constructs_fail_closed(
    solution: str, expected_error: str
):
    result = verify_submission("python-normalize-records-v1", solution)

    assert result["passed"] is False
    assert expected_error in (result["error"] or "")
    assert result["tests_passed"] == 0


def test_python_runtime_error_cannot_pass():
    result = verify_submission(
        "python-normalize-records-v1",
        "def normalize_records(records):\n    return 1 / 0\n",
    )

    assert result["passed"] is False
    assert result["tests_passed"] == 0


def test_python_infinite_loop_times_out_and_fails_closed():
    result = verify_submission(
        "python-normalize-records-v1",
        "def normalize_records(records):\n    while True:\n        pass\n",
        timeout_seconds=0.2,
    )

    assert result["passed"] is False
    assert "timed out" in (result["error"] or "").lower()


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM users",
        "SELECT name FROM users; DELETE FROM users;",
        "PRAGMA table_info(users)",
        "ATTACH DATABASE '/tmp/escape.db' AS outside",
    ],
)
def test_sql_rejects_mutation_multiple_statements_and_unsafe_commands(query: str):
    result = verify_submission("sql-customer-orders-v1", query)

    assert result["passed"] is False
    assert result["tests_passed"] == 0
    assert result["error"]


def test_unknown_template_fails_closed():
    result = verify_submission("not-a-template", "anything")

    assert result == {
        "passed": False,
        "tests_passed": 0,
        "tests_total": 0,
        "test_results": [],
        "runtime_ms": 0,
        "error": "Unsupported challenge template.",
    }
