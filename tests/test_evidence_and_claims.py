from __future__ import annotations

from datetime import datetime, timezone

from backend.engines.evidence_validation_engine import EvidenceValidationEngine
from backend.engines.skill_claim_engine import SkillClaimEngine
from backend.models.schemas import (
    ChallengeLevel,
    EvidenceDirectness,
    EvidenceSourceType,
    SkillState,
    VerificationEvent,
)


STUDENT_ID = "STU-DEMO-IND-001"


def _claims_for(student: dict, snapshot: dict, academic: list[dict]):
    evidence = EvidenceValidationEngine().analyze(student, snapshot, academic)
    claims = SkillClaimEngine().build(student["id"], evidence, [])
    return evidence, {claim.skill: claim for claim in claims}


def _event(*, skill: str, claim_id: str, passed: bool) -> VerificationEvent:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    return VerificationEvent(
        id=f"VER-{skill.upper()}",
        student_id=STUDENT_ID,
        claim_id=claim_id,
        challenge_id=f"CHL-{skill.upper()}",
        attempt_id=f"ATT-{skill.upper()}",
        skill=skill,
        level=ChallengeLevel.INTERMEDIATE,
        passed=passed,
        tests_passed=5 if passed else 4,
        tests_total=5,
        started_at=now,
        completed_at=now,
        template_version="1.0",
        submission_hash="a" * 64,
        evidence_hash="b" * 64,
    )


def test_repository_metadata_alone_does_not_create_evidence(demo_student: dict):
    snapshot = {
        "repository_url": "https://github.com/example/metadata-only",
        "branch": "main",
        "technologies": ["Python", "FastAPI", "SQL"],
        "files": [],
        "commits": [],
    }

    evidence = EvidenceValidationEngine().analyze(demo_student, snapshot, [])

    assert evidence == []


def test_academic_evidence_is_contextual_and_never_self_verifies(
    demo_student: dict, demo_academic_records: list[dict]
):
    evidence, claims = _claims_for(demo_student, {"files": [], "commits": []}, demo_academic_records)

    assert evidence
    assert all(item.source_type is EvidenceSourceType.ACADEMIC for item in evidence)
    assert all(item.directness is EvidenceDirectness.CONTEXTUAL for item in evidence)
    assert all("Demo academic evidence" in item.title for item in evidence)
    assert all(claim.state is SkillState.DETECTED for claim in claims.values())


def test_dependency_only_is_detected_not_evidence_backed(demo_student: dict):
    snapshot = {
        "repository_url": "https://github.com/example/dependency-only",
        "branch": "main",
        "files": [{"path": "requirements.txt", "content": "fastapi==1.0\n"}],
        "commits": [],
    }

    _, claims = _claims_for(demo_student, snapshot, [])

    assert claims["FastAPI"].state is SkillState.DETECTED


def test_independent_implementation_and_test_signals_become_evidence_backed(
    demo_student: dict,
):
    snapshot = {
        "repository_url": "https://github.com/example/api",
        "branch": "main",
        "files": [
            {"path": "requirements.txt", "content": "fastapi==1.0\n"},
            {
                "path": "app/routes.py",
                "content": "from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/users')\ndef users(): return []\n",
            },
            {
                "path": "tests/test_routes.py",
                "content": "from fastapi.testclient import TestClient\ndef test_users(client: TestClient):\n    assert client.get('/users').status_code == 200\n",
            },
        ],
        "commits": [],
    }

    _, claims = _claims_for(demo_student, snapshot, [])

    assert claims["FastAPI"].state is SkillState.EVIDENCE_BACKED


def test_failed_event_cannot_promote_evidence_backed_claim(
    demo_student: dict, demo_snapshot: dict, demo_academic_records: list[dict]
):
    evidence, claims = _claims_for(demo_student, demo_snapshot, demo_academic_records)
    original = claims["FastAPI"]
    failed = _event(skill="FastAPI", claim_id=original.id, passed=False)

    rebuilt = {
        claim.skill: claim
        for claim in SkillClaimEngine().build(demo_student["id"], evidence, [failed])
    }

    assert original.state is SkillState.EVIDENCE_BACKED
    assert rebuilt["FastAPI"].state is SkillState.EVIDENCE_BACKED
    assert rebuilt["FastAPI"].verification_event_id is None


def test_passing_event_is_the_only_input_that_promotes_claim(
    demo_student: dict, demo_snapshot: dict, demo_academic_records: list[dict]
):
    evidence, claims = _claims_for(demo_student, demo_snapshot, demo_academic_records)
    original = claims["FastAPI"]
    passed = _event(skill="FastAPI", claim_id=original.id, passed=True)

    rebuilt = {
        claim.skill: claim
        for claim in SkillClaimEngine().build(demo_student["id"], evidence, [passed])
    }

    assert rebuilt["FastAPI"].state is SkillState.CHALLENGE_VERIFIED
    assert rebuilt["FastAPI"].verification_event_id == passed.id
    assert rebuilt["FastAPI"].verified_level is ChallengeLevel.INTERMEDIATE


def test_demo_snapshot_produces_inspectable_provenance(
    demo_student: dict, demo_snapshot: dict, demo_academic_records: list[dict]
):
    evidence, claims = _claims_for(demo_student, demo_snapshot, demo_academic_records)

    fastapi = [item for item in evidence if item.skill == "FastAPI"]
    assert fastapi
    assert all(item.source_ref for item in fastapi)
    assert any(item.source_ref == "app/routes/users.py" for item in fastapi)
    assert any(item.source_ref == "tests/test_users.py" for item in fastapi)
    assert claims["FastAPI"].state is SkillState.EVIDENCE_BACKED
