from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.engines.opportunity_matching_engine import OpportunityMatchingEngine
from backend.models.schemas import (
    Opportunity,
    OpportunityRequirement,
    RequirementImportance,
    RequirementState,
    SkillState,
)
from backend.services.gemini_service import GeminiService


def _settings(tmp_path, fixture_path, *, gemini_api_key=None) -> Settings:
    return Settings(
        store_path=tmp_path / "runtime.json",
        fixture_path=fixture_path,
        mongodb_uri=None,
        mongodb_database="skillpassport_test",
        github_token=None,
        gemini_api_key=gemini_api_key,
        gemini_model="test-model",
        challenge_timeout_seconds=1.0,
        public_base_url=None,
    )


def test_no_key_gemini_service_is_explicitly_unavailable(tmp_path, fixture_path):
    service = GeminiService(_settings(tmp_path, fixture_path, gemini_api_key=None))

    assert service.available is False
    assert service.extract_opportunity("Python and SQL are required.") is None


def test_no_key_english_opportunity_falls_back_to_taxonomy(
    tmp_path, fixture_path
):
    engine = OpportunityMatchingEngine(
        GeminiService(_settings(tmp_path, fixture_path, gemini_api_key=None))
    )
    description = (
        "Python, FastAPI, and SQL are required capabilities for this backend role. "
        "Docker is preferred."
    )

    opportunity = engine.parse(
        "Backend Intern", "Example Company", "Japan", description
    )
    by_skill = {item.skill: item for item in opportunity.requirements}

    assert opportunity.original_language == "English"
    assert set(by_skill) == {"Python", "FastAPI", "SQL", "Docker"}
    assert by_skill["Python"].importance is RequirementImportance.REQUIRED
    assert by_skill["FastAPI"].importance is RequirementImportance.REQUIRED
    assert by_skill["SQL"].importance is RequirementImportance.REQUIRED
    assert by_skill["Docker"].importance is RequirementImportance.PREFERRED


def test_no_key_japanese_opportunity_preserves_required_and_preferred_distinction(
    tmp_path, fixture_path
):
    engine = OpportunityMatchingEngine(
        GeminiService(_settings(tmp_path, fixture_path, gemini_api_key=None))
    )
    description = (
        "東京のバックエンドインターン。Python、FastAPI、SQL は必須です。"
        "Docker と日本語 B1 は歓迎します。"
    )

    opportunity = engine.parse(
        "Tokyo Backend Internship", "Example Company", "Japan", description
    )
    by_skill = {item.skill: item for item in opportunity.requirements}

    assert opportunity.original_language == "Japanese or mixed"
    assert by_skill["Python"].importance is RequirementImportance.REQUIRED
    assert by_skill["FastAPI"].importance is RequirementImportance.REQUIRED
    assert by_skill["SQL"].importance is RequirementImportance.REQUIRED
    assert by_skill["Docker"].importance is RequirementImportance.PREFERRED
    assert by_skill["Japanese B1"].importance is RequirementImportance.PREFERRED


def test_matching_keeps_verified_backed_detected_and_missing_distinct(
    tmp_path, fixture_path
):
    engine = OpportunityMatchingEngine(
        GeminiService(_settings(tmp_path, fixture_path, gemini_api_key=None))
    )
    opportunity = Opportunity(
        id="OPP-TEST",
        title="Transparent Backend Role",
        company="Example Company",
        country="Japan",
        description="Python, FastAPI, Japanese B1 and Docker are required.",
        requirements=[
            OpportunityRequirement(
                skill="Python",
                importance=RequirementImportance.REQUIRED,
                source_text="Python is required",
            ),
            OpportunityRequirement(
                skill="FastAPI",
                importance=RequirementImportance.REQUIRED,
                source_text="FastAPI is required",
            ),
            OpportunityRequirement(
                skill="Japanese B1",
                importance=RequirementImportance.REQUIRED,
                source_text="Japanese B1 is required",
            ),
            OpportunityRequirement(
                skill="Docker",
                importance=RequirementImportance.REQUIRED,
                source_text="Docker is required",
            ),
            OpportunityRequirement(
                skill="SQL",
                importance=RequirementImportance.PREFERRED,
                source_text="SQL is preferred",
            ),
        ],
    )
    claims = [
        {
            "id": "CLM-PYTHON",
            "skill": "Python",
            "state": SkillState.CHALLENGE_VERIFIED.value,
            "challenge_available": True,
        },
        {
            "id": "CLM-FASTAPI",
            "skill": "FastAPI",
            "state": SkillState.EVIDENCE_BACKED.value,
            "challenge_available": True,
        },
        {
            "id": "CLM-JAPANESE",
            "skill": "Japanese B1",
            "state": SkillState.DETECTED.value,
            "challenge_available": False,
        },
        {
            "id": "CLM-SQL",
            "skill": "SQL",
            "state": SkillState.EVIDENCE_BACKED.value,
            "challenge_available": True,
        },
    ]

    coverage = engine.match(opportunity, claims)
    by_skill = {item.requirement.skill: item for item in coverage.matches}

    assert by_skill["Python"].state is RequirementState.CHALLENGE_VERIFIED
    assert by_skill["FastAPI"].state is RequirementState.EVIDENCE_BACKED
    assert by_skill["Japanese B1"].state is RequirementState.DETECTED
    assert by_skill["Docker"].state is RequirementState.MISSING
    assert by_skill["FastAPI"].action_available is True
    assert by_skill["Python"].action_available is False
    assert by_skill["Japanese B1"].action_available is False
    assert coverage.required_total == 4
    assert coverage.required_challenge_verified == 1
    assert coverage.required_evidence_backed == 1
    assert coverage.required_detected == 1
    assert coverage.required_missing == 1
    assert coverage.preferred_total == 1


def test_unrecognizable_opportunity_fails_instead_of_inventing_requirements(
    tmp_path, fixture_path
):
    engine = OpportunityMatchingEngine(
        GeminiService(_settings(tmp_path, fixture_path, gemini_api_key=None))
    )

    with pytest.raises(ValueError, match="recognizable capability"):
        engine.parse(
            "Ambiguous Role",
            "Example Company",
            "Japan",
            "Bring curiosity and collaborate with the team every day.",
        )
