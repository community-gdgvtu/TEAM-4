from __future__ import annotations

import pytest

from backend.challenges.templates import get_template
from backend.core.config import Settings
from backend.engines.evidence_validation_engine import EvidenceValidationEngine
from backend.engines.proof_verification_engine import ProofVerificationEngine
from backend.engines.skill_claim_engine import SkillClaimEngine
from backend.models.schemas import SkillState
from backend.services.academic_service import AcademicService
from backend.services.persistence import JsonStore


STUDENT_ID = "STU-DEMO-IND-001"


def _settings(tmp_path, fixture_path) -> Settings:
    return Settings(
        store_path=tmp_path / "runtime.json",
        fixture_path=fixture_path,
        mongodb_uri=None,
        mongodb_database="skillpassport_test",
        github_token=None,
        gemini_api_key=None,
        gemini_model="test-model",
        challenge_timeout_seconds=1.0,
        public_base_url=None,
    )


def _hydrated_engine(tmp_path, fixture_path):
    settings = _settings(tmp_path, fixture_path)
    store = JsonStore(settings.store_path, settings.fixture_path)
    data = store.read()
    student = next(item for item in data["students"] if item["id"] == STUDENT_ID)
    snapshot = next(
        item for item in data["repo_snapshots"] if item["student_id"] == STUDENT_ID
    )
    academic = AcademicService().records_for_student(data, student)
    evidence = EvidenceValidationEngine().analyze(student, snapshot, academic)
    claims = SkillClaimEngine().build(STUDENT_ID, evidence, [])

    def persist(values: dict) -> None:
        values["evidence_items"] = [item.model_dump(mode="json") for item in evidence]
        values["claims"] = [item.model_dump(mode="json") for item in claims]

    store.update(persist)
    return ProofVerificationEngine(store, settings), store, settings


def _claim(store: JsonStore, skill: str) -> dict:
    return next(item for item in store.read()["claims"] if item["skill"] == skill)


def _perfect_concepts(template_id: str) -> dict[str, int]:
    template = get_template(template_id)
    return {
        question["id"]: question["correct"]
        for question in template["concept_questions"]
    }


def test_failed_live_task_with_perfect_concepts_cannot_promote_claim(
    tmp_path, fixture_path
):
    engine, store, _ = _hydrated_engine(tmp_path, fixture_path)
    initial = _claim(store, "FastAPI")
    challenge = engine.create_challenge(STUDENT_ID, initial["id"])

    result = engine.submit(
        challenge.id,
        STUDENT_ID,
        _perfect_concepts(challenge.template_id),
        "def create_user(payload, users):\n    return {'status_code': 201, 'body': payload}\n",
    )

    persisted = store.read()
    current = _claim(store, "FastAPI")
    assert result["attempt"]["concept_correct"] == result["attempt"]["concept_total"]
    assert result["attempt"]["passed"] is False
    assert result["verification_event"] is None
    assert current["state"] == SkillState.EVIDENCE_BACKED.value
    assert current["verification_event_id"] is None
    assert persisted["verification_events"] == []
    assert persisted["passports"] == []


@pytest.mark.parametrize("skill", ["Python", "FastAPI", "SQL"])
def test_passing_supported_proof_creates_event_promotes_claim_and_issues_stamp(
    skill: str, tmp_path, fixture_path
):
    engine, store, _ = _hydrated_engine(tmp_path, fixture_path)
    initial = _claim(store, skill)
    assert initial["state"] == SkillState.EVIDENCE_BACKED.value
    challenge = engine.create_challenge(STUDENT_ID, initial["id"])
    solution = get_template(challenge.template_id)["demo_solution"]

    result = engine.submit(challenge.id, STUDENT_ID, {}, solution)

    current = _claim(store, skill)
    assert result["attempt"]["passed"] is True
    assert result["verification_event"]["passed"] is True
    assert len(result["verification_event"]["evidence_hash"]) == 64
    assert current["state"] == SkillState.CHALLENGE_VERIFIED.value
    assert current["verification_event_id"] == result["verification_event"]["id"]
    assert result["passport"]["stamps"]
    stamp = next(item for item in result["passport"]["stamps"] if item["skill"] == skill)
    assert stamp["verification_event_id"] == result["verification_event"]["id"]


def test_verification_event_and_promoted_claim_survive_store_reinstantiation(
    tmp_path, fixture_path
):
    engine, store, settings = _hydrated_engine(tmp_path, fixture_path)
    claim = _claim(store, "FastAPI")
    challenge = engine.create_challenge(STUDENT_ID, claim["id"])
    solution = get_template(challenge.template_id)["demo_solution"]
    result = engine.submit(challenge.id, STUDENT_ID, {}, solution)

    reopened = JsonStore(settings.store_path, settings.fixture_path).read()

    event_id = result["verification_event"]["id"]
    assert any(item["id"] == event_id for item in reopened["verification_events"])
    persisted_claim = next(item for item in reopened["claims"] if item["skill"] == "FastAPI")
    assert persisted_claim["state"] == SkillState.CHALLENGE_VERIFIED.value
    assert persisted_claim["verification_event_id"] == event_id
    assert any(
        stamp["verification_event_id"] == event_id
        for passport in reopened["passports"]
        for stamp in passport["stamps"]
    )


def test_cross_student_submission_is_rejected(tmp_path, fixture_path):
    engine, store, _ = _hydrated_engine(tmp_path, fixture_path)
    claim = _claim(store, "FastAPI")
    challenge = engine.create_challenge(STUDENT_ID, claim["id"])

    with pytest.raises(KeyError, match="Proof challenge not found"):
        engine.submit(
            challenge.id,
            "STU-OTHER",
            {},
            get_template(challenge.template_id)["demo_solution"],
        )

    assert store.read()["verification_events"] == []


def test_challenge_cannot_be_reused_after_passing(tmp_path, fixture_path):
    engine, store, _ = _hydrated_engine(tmp_path, fixture_path)
    claim = _claim(store, "SQL")
    challenge = engine.create_challenge(STUDENT_ID, claim["id"])
    solution = get_template(challenge.template_id)["demo_solution"]
    engine.submit(challenge.id, STUDENT_ID, {}, solution)

    with pytest.raises(ValueError, match="already passed"):
        engine.submit(challenge.id, STUDENT_ID, {}, solution)
