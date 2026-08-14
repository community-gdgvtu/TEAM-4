from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.academic_service import AcademicService


DEMO_FIXTURE_PATH = ROOT / "data" / "demo" / "fixture.json"
DEMO_STUDENT_ID = "STU-DEMO-IND-001"


@pytest.fixture
def fixture_path() -> Path:
    return DEMO_FIXTURE_PATH


@pytest.fixture
def demo_data(fixture_path: Path) -> dict:
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def demo_student(demo_data: dict) -> dict:
    student = next(
        item for item in demo_data["students"] if item["id"] == DEMO_STUDENT_ID
    )
    return copy.deepcopy(student)


@pytest.fixture
def demo_snapshot(demo_data: dict) -> dict:
    snapshot = next(
        item
        for item in demo_data["repo_snapshots"]
        if item["student_id"] == DEMO_STUDENT_ID
    )
    return copy.deepcopy(snapshot)


@pytest.fixture
def demo_academic_records(demo_data: dict, demo_student: dict) -> list[dict]:
    return AcademicService().records_for_student(demo_data, demo_student)
