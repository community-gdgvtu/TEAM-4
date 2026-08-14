"""Small local/demo authentication service using salted scrypt password hashes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any

from backend.engines.evidence_validation_engine import stable_id
from backend.models.schemas import LoginRequest, SignupRequest
from backend.services.persistence import Store


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
    return "$".join(
        ["scrypt", str(n), str(r), str(p), base64.b64encode(salt).decode(), base64.b64encode(digest).decode()]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, store: Store):
        self.store = store

    def signup(self, request: SignupRequest) -> dict[str, Any]:
        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            if any(user.get("email", "").lower() == request.email for user in data.get("users", [])):
                raise ValueError("An account already exists for this email")
            student_id = stable_id("STU", request.email)
            user_id = stable_id("USER", request.email)
            student = {
                "id": student_id,
                "display_name": request.name,
                "email": request.email,
                "institution": request.institution,
                "country": request.country,
                "study_area": request.study_area,
                "headline": f"{request.study_area} student",
                "github_username": request.github_username,
                "repository_url": request.repository_url,
                "academic_source": request.academic_source,
                "manual_coursework": [item.model_dump(mode="json") for item in request.manual_coursework],
                "demo": False,
            }
            user = {
                "id": user_id,
                "student_id": student_id,
                "email": request.email,
                "password_hash": hash_password(request.password),
                "demo": False,
            }
            data.setdefault("students", []).append(student)
            data.setdefault("users", []).append(user)
            if request.academic_source == "demo":
                data.setdefault("academic_records", []).extend(
                    [
                        {
                            "id": stable_id("ACAD", student_id, "Programming Foundations"),
                            "student_id": student_id,
                            "course_name": "Programming Foundations (Selected Demo Record)",
                            "grade": "B+",
                            "skills": ["Python"],
                            "institution": request.institution,
                            "demo": True,
                        },
                        {
                            "id": stable_id("ACAD", student_id, "Database Systems"),
                            "student_id": student_id,
                            "course_name": "Database Systems (Selected Demo Record)",
                            "grade": "B+",
                            "skills": ["SQL"],
                            "institution": request.institution,
                            "demo": True,
                        },
                    ]
                )
            return self._session(data, user, student)

        return self.store.update(mutate)

    def login(self, request: LoginRequest) -> dict[str, Any]:
        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            user = next(
                (item for item in data.get("users", []) if item.get("email", "").lower() == request.email.lower()),
                None,
            )
            if not user or not verify_password(request.password, user.get("password_hash", "")):
                raise PermissionError("Invalid email or password")
            student = next(item for item in data.get("students", []) if item.get("id") == user.get("student_id"))
            return self._session(data, user, student)

        return self.store.update(mutate)

    @staticmethod
    def _session(data: dict[str, Any], user: dict[str, Any], student: dict[str, Any]) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        data.setdefault("sessions", []).append(
            {"id": stable_id("SES", token), "token_hash": hashlib.sha256(token.encode()).hexdigest(), "user_id": user["id"], "student_id": student["id"]}
        )
        return {"token": token, "user": {"id": user["id"], "email": user["email"], "demo": user.get("demo", False)}, "student": student}

