"""Narrow deterministic execution runner for allowlisted proof templates.

This is defense-in-depth isolation for a constrained MVP, not a production
multi-tenant sandbox. Production requires container/VM isolation and enforced
network denial.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import resource
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any


FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.AsyncFunctionDef,
    ast.Await,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
)
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "input", "breakpoint", "help",
    "memoryview", "classmethod", "staticmethod", "property", "type", "object",
}


def _validate_python(source: str, expected_function: str) -> str | None:
    if len(source.encode("utf-8")) > 20_000:
        return "Submission is too large."
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError:
        return "Submission contains invalid Python syntax."
    if sum(1 for _ in ast.walk(tree)) > 1_500:
        return "Submission is too complex."
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if not any(node.name == expected_function for node in functions):
        return f"Define the required function {expected_function}()."
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            return f"{type(node).__name__} is not allowed in this challenge."
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return f"Use of {node.id} is not allowed."
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return "Private or dunder attribute access is not allowed."
    if any(
        not isinstance(node, ast.FunctionDef)
        and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        for node in tree.body
    ):
        return "Only the required function definition is allowed at module level."
    return None


def _limits() -> None:
    def best_effort(kind: int, soft: int, hard: int) -> None:
        try:
            _current_soft, current_hard = resource.getrlimit(kind)
            if current_hard != resource.RLIM_INFINITY:
                hard = min(hard, current_hard)
            soft = min(soft, hard)
            resource.setrlimit(kind, (soft, hard))
        except (OSError, ValueError):
            pass

    best_effort(resource.RLIMIT_CPU, 2, 2)
    # A low RLIMIT_AS can prevent Python itself from launching on Darwin.
    if sys.platform != "darwin":
        best_effort(resource.RLIMIT_AS, 512 * 1024 * 1024, 512 * 1024 * 1024)
    best_effort(resource.RLIMIT_FSIZE, 1024 * 1024, 1024 * 1024)
    best_effort(resource.RLIMIT_NOFILE, 32, 32)
    if hasattr(resource, "RLIMIT_NPROC") and sys.platform != "darwin":
        best_effort(resource.RLIMIT_NPROC, 1, 1)


def _python_harness(template_id: str) -> tuple[str, str]:
    if template_id == "python-normalize-records-v1":
        return "normalize_records", r'''
tests = []
def check(name, condition, detail):
    tests.append({"name": name, "passed": bool(condition), "detail": detail})

source = [
    {"email": " B@Example.com ", "name": "Bea"},
    {"email": "a@example.com", "name": "Ari"},
    {"email": "b@example.COM", "name": "Replacement"},
    {"email": "", "name": "Missing"},
]
before = repr(source)
try:
    result = target(source)
    check("normalizes-email", isinstance(result, list) and all(item.get("email") == item.get("email", "").strip().lower() for item in result), "Emails are normalized.")
    check("deduplicates", result == [{"email": "a@example.com", "name": "Ari"}, {"email": "b@example.com", "name": "Bea"}], "First valid normalized record is retained.")
    check("stable-order", [item["email"] for item in result] == sorted(item["email"] for item in result), "Rows are sorted by email.")
    check("ignores-invalid", all(item.get("email") for item in result), "Invalid empty email is ignored.")
    check("input-preserved", repr(source) == before, "Input records are not mutated.")
except Exception:
    check("execution", False, "The function raised an exception.")
print(json.dumps({"tests": tests}))
'''
    if template_id == "fastapi-duplicate-email-v1":
        return "create_user", r'''
tests = []
def check(name, condition, detail):
    tests.append({"name": name, "passed": bool(condition), "detail": detail})

users = {}
try:
    created = target({"name": "Asha", "email": "Asha@Example.com"}, users)
    check("creation-preserved", created == {"status_code": 201, "body": {"name": "Asha", "email": "asha@example.com"}}, "New user returns 201 with normalized data.")
    check("stored", users.get("asha@example.com", {}).get("name") == "Asha", "New user is persisted in the supplied store.")
    duplicate = target({"name": "Overwrite", "email": " ASHA@example.COM "}, users)
    check("duplicate-conflict", duplicate == {"status_code": 409, "body": {"detail": "Email already exists"}}, "Duplicate returns exact 409 response.")
    check("case-insensitive", len(users) == 1, "Case variants share one uniqueness key.")
    check("no-regression", users["asha@example.com"]["name"] == "Asha", "Rejected duplicate does not overwrite existing data.")
except Exception:
    check("execution", False, "The function raised an exception.")
print(json.dumps({"tests": tests}))
'''
    raise KeyError("Unsupported executable template")


def _run_python(template_id: str, solution: str, timeout_seconds: float) -> dict[str, Any]:
    expected_function, tests = _python_harness(template_id)
    validation_error = _validate_python(solution, expected_function)
    if validation_error:
        return _result([], validation_error, 0)

    bootstrap = f'''import json\nSAFE = {{name: value for name, value in {{"str": str, "dict": dict, "list": list, "set": set, "tuple": tuple, "len": len, "sorted": sorted, "enumerate": enumerate, "range": range, "min": min, "max": max, "sum": sum, "any": any, "all": all, "isinstance": isinstance, "bool": bool, "int": int, "float": float}}.items()}}\nnamespace = {{"__builtins__": SAFE}}\nsource = open({json.dumps('submission.py')}, encoding="utf-8").read()\nexec(compile(source, "submission.py", "exec"), namespace)\ntarget = namespace[{json.dumps(expected_function)}]\n{tests}\n'''
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="skillpassport-challenge-") as temp_dir:
        directory = Path(temp_dir)
        (directory / "submission.py").write_text(solution, encoding="utf-8")
        (directory / "runner.py").write_text(bootstrap, encoding="utf-8")
        env = {"PATH": os.defpath, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(directory / "runner.py")],
                cwd=directory,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                start_new_session=True,
                preexec_fn=_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return _result([], "Execution timed out.", int((time.perf_counter() - start) * 1000))
        except (subprocess.SubprocessError, OSError):
            return _result([], "Challenge runner could not start safely.", int((time.perf_counter() - start) * 1000))
    runtime_ms = int((time.perf_counter() - start) * 1000)
    if completed.returncode != 0:
        return _result([], "Submission could not be evaluated safely.", runtime_ms)
    try:
        payload = json.loads(completed.stdout[-100_000:])
        return _result(payload.get("tests", []), None, runtime_ms)
    except (json.JSONDecodeError, AttributeError):
        return _result([], "Challenge runner returned an invalid result.", runtime_ms)


def _sql_authorizer(action: int, _arg1: str, _arg2: str, _db: str, _source: str) -> int:
    denied = {
        sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_TRANSACTION,
    }
    return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK


def _run_sql(solution: str) -> dict[str, Any]:
    start = time.perf_counter()
    query = solution.strip()
    if len(query) > 10_000 or not query.lower().startswith(("select", "with")):
        return _result([], "Submit one read-only SELECT query.", 0)
    if ";" in query.rstrip(";"):
        return _result([], "Only one SQL statement is allowed.", 0)
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(
            "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
            "CREATE TABLE registrations(user_id INTEGER, event_id INTEGER);"
            "INSERT INTO users VALUES(1,'Asha'),(2,'Kenji'),(3,'Mina');"
            "INSERT INTO registrations VALUES(1,10),(1,11),(3,12);"
        )
        remaining = 20_000
        def progress() -> int:
            nonlocal remaining
            remaining -= 1
            return int(remaining <= 0)
        connection.set_progress_handler(progress, 100)
        connection.set_authorizer(_sql_authorizer)
        cursor = connection.execute(query)
        rows = cursor.fetchmany(101)
        columns = [item[0].lower() for item in (cursor.description or [])]
        expected = [("Asha", 2), ("Mina", 1), ("Kenji", 0)]
        tests = [
            {"name": "read-only", "passed": True, "detail": "Query executed under the read-only authorizer."},
            {"name": "columns", "passed": columns == ["name", "event_count"], "detail": "Columns are name and event_count."},
            {"name": "all-users", "passed": len(rows) == 3 and any(row[0] == "Kenji" and row[1] == 0 for row in rows), "detail": "Users with zero registrations remain."},
            {"name": "correct-counts", "passed": rows == expected, "detail": "Counts and deterministic ordering match the fixture."},
            {"name": "bounded-result", "passed": len(rows) <= 100, "detail": "Result stays within the challenge bound."},
        ]
        return _result(tests, None, int((time.perf_counter() - start) * 1000))
    except sqlite3.Error:
        return _result([], "SQL could not be evaluated or attempted a disallowed operation.", int((time.perf_counter() - start) * 1000))
    finally:
        connection.close()


def _result(tests: list[dict[str, Any]], error: str | None, runtime_ms: int) -> dict[str, Any]:
    sanitized = [
        {"name": str(test.get("name", "test")), "passed": bool(test.get("passed")), "detail": str(test.get("detail", ""))[:300]}
        for test in tests
    ]
    passed_count = sum(test["passed"] for test in sanitized)
    return {
        "passed": bool(sanitized) and passed_count == len(sanitized) and error is None,
        "tests_passed": passed_count,
        "tests_total": len(sanitized),
        "test_results": sanitized,
        "runtime_ms": runtime_ms,
        "error": error,
    }


def verify_submission(template_id: str, solution: str, timeout_seconds: float = 3.0) -> dict[str, Any]:
    if template_id == "sql-customer-orders-v1":
        return _run_sql(solution)
    if template_id in {"python-normalize-records-v1", "fastapi-duplicate-email-v1"}:
        return _run_python(template_id, solution, timeout_seconds)
    return _result([], "Unsupported challenge template.", 0)
