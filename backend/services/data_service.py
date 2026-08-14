"""Compatibility helpers backed by the active persistence adapter.

New code should depend on the Store protocol directly. These functions replace
the original dead CSV paths and are retained only for small integrations.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import get_settings
from backend.services.persistence import create_store


def get_runtime_data() -> dict[str, Any]:
    return create_store(get_settings()).read()


def get_students() -> list[dict[str, Any]]:
    return get_runtime_data().get("students", [])


def get_student(student_id: str) -> dict[str, Any] | None:
    return next((item for item in get_students() if item.get("id") == student_id), None)


def get_jobs() -> list[dict[str, Any]]:
    return get_runtime_data().get("opportunities", [])


def get_evidence() -> list[dict[str, Any]]:
    return get_runtime_data().get("evidence_items", [])
