from __future__ import annotations

import json

import pytest

from backend.models.schemas import LoginRequest, SignupRequest
from backend.services.auth_service import AuthService, hash_password, verify_password
from backend.services.persistence import JsonStore


def _request(email: str = "candidate@example.test", password: str = "correct horse battery"):
    return SignupRequest(
        name="Fictional Candidate",
        email=email,
        password=password,
        institution="Example Institute",
        country="India",
        study_area="Computer Science",
        academic_source="manual",
        manual_coursework=[
            {"course_name": "Database Systems", "grade": "A", "skills": ["SQL"]}
        ],
    )


def test_password_hashes_are_salted_and_verifiable():
    password = "not stored in plaintext"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("scrypt$")
    assert second.startswith("scrypt$")
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("wrong password", first)


def test_signup_never_persists_plaintext_password_or_session_token(
    tmp_path, fixture_path
):
    store = JsonStore(tmp_path / "runtime.json", fixture_path)
    service = AuthService(store)
    password = "unique plaintext sentinel 456"

    response = service.signup(_request(password=password))
    persisted = store.read()
    serialized = json.dumps(persisted, sort_keys=True)
    user = next(item for item in persisted["users"] if item["email"] == "candidate@example.test")

    assert password not in serialized
    assert "password" not in user
    assert verify_password(password, user["password_hash"])
    assert response["token"] not in serialized
    assert all("token" not in session for session in persisted["sessions"])
    assert all("token_hash" in session for session in persisted["sessions"])
    assert "password" not in json.dumps(response)


def test_signup_rejects_duplicate_email(tmp_path, fixture_path):
    store = JsonStore(tmp_path / "runtime.json", fixture_path)
    service = AuthService(store)
    service.signup(_request())

    with pytest.raises(ValueError, match="already exists"):
        service.signup(_request(email="CANDIDATE@example.test"))


def test_login_accepts_correct_password_and_rejects_wrong_password(
    tmp_path, fixture_path
):
    store = JsonStore(tmp_path / "runtime.json", fixture_path)
    service = AuthService(store)
    password = "correct horse battery"
    service.signup(_request(password=password))

    logged_in = service.login(
        LoginRequest(email="candidate@example.test", password=password)
    )

    assert logged_in["student"]["display_name"] == "Fictional Candidate"
    with pytest.raises(PermissionError, match="Invalid email or password"):
        service.login(
            LoginRequest(email="candidate@example.test", password="wrong password")
        )
