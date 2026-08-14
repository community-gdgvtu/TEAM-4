"""The only component allowed to promote a claim to CHALLENGE_VERIFIED."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import secrets
from typing import Any

from backend.challenges.runner import verify_submission
from backend.challenges.templates import (
    get_template,
    public_template,
    score_concepts,
    template_for_skill,
)
from backend.core.config import Settings
from backend.models.schemas import (
    ChallengeAttempt,
    ChallengeLevel,
    ChallengeStatus,
    ProofChallenge,
    SkillState,
    VerificationEvent,
)
from backend.services.passport_service import build_passport
from backend.services.persistence import Store, find_by_id
from backend.services.gemini_service import GeminiService


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(6).upper()}"


class ProofVerificationEngine:
    def __init__(self, store: Store, settings: Settings):
        self.store = store
        self.settings = settings
        self.gemini = GeminiService(settings)

    def create_challenge(self, student_id: str, claim_id: str) -> ProofChallenge:
        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            claim = find_by_id(data, "claims", claim_id)
            if not claim or claim.get("student_id") != student_id:
                raise KeyError("Skill claim not found")
            if not claim.get("challenge_available"):
                raise ValueError("Live proof is not available for this skill")
            template = template_for_skill(claim["skill"])
            if not template:
                raise ValueError("Live proof is not available for this skill")
            student = find_by_id(data, "students", student_id) or {}
            evidence_by_id = {item["id"]: item for item in data.get("evidence_items", [])}
            source_context = [
                evidence_by_id[item_id]["source_ref"]
                for item_id in claim.get("evidence_ids", [])
                if item_id in evidence_by_id
            ][:8]
            visible = public_template(template, include_demo_solution=bool(student.get("demo")))
            personalized = self.gemini.personalize_challenge(
                skill=claim["skill"],
                source_context=source_context,
                title=visible["title"],
                rationale=visible["rationale"],
                instructions=visible["instructions"],
            )
            if personalized:
                visible.update(personalized.model_dump())
            challenge = ProofChallenge(
                id=_new_id("CH"),
                student_id=student_id,
                claim_id=claim_id,
                skill=claim["skill"],
                challenge_type=visible["challenge_type"],
                level=visible["level"],
                template_id=visible["template_id"],
                template_version=visible["version"],
                title=visible["title"],
                rationale=visible["rationale"],
                source_context=source_context,
                instructions=visible["instructions"],
                starter_code=visible["starter_code"],
                concept_questions=visible["concept_questions"],
                public_tests=visible["public_tests"],
                demo_solution=visible.get("demo_solution"),
                created_at=datetime.now(timezone.utc),
            )
            data.setdefault("challenges", []).append(challenge.model_dump(mode="json"))
            return challenge.model_dump(mode="json")

        return ProofChallenge.model_validate(self.store.update(mutate))

    def get_challenge(self, challenge_id: str) -> ProofChallenge | None:
        value = find_by_id(self.store.read(), "challenges", challenge_id)
        return ProofChallenge.model_validate(value) if value else None

    def submit(
        self,
        challenge_id: str,
        student_id: str,
        concept_answers: dict[str, int],
        solution: str,
    ) -> dict[str, Any]:
        snapshot = self.store.read()
        challenge = find_by_id(snapshot, "challenges", challenge_id)
        if not challenge or challenge.get("student_id") != student_id:
            raise KeyError("Proof challenge not found")
        if challenge.get("status") == ChallengeStatus.PASSED.value:
            raise ValueError("This challenge has already passed")
        template = get_template(challenge["template_id"])
        started = datetime.now(timezone.utc)
        runner_result = verify_submission(
            challenge["template_id"], solution, self.settings.challenge_timeout_seconds
        )
        completed = datetime.now(timezone.utc)
        concept_correct, concept_total = score_concepts(template, concept_answers)
        submission_hash = hashlib.sha256(solution.encode("utf-8")).hexdigest()

        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            persisted_challenge = find_by_id(data, "challenges", challenge_id)
            claim = find_by_id(data, "claims", challenge["claim_id"])
            if not persisted_challenge or not claim or claim.get("student_id") != student_id:
                raise KeyError("Challenge state changed")
            if persisted_challenge.get("status") == ChallengeStatus.PASSED.value:
                raise ValueError("This challenge has already passed")
            attempt = ChallengeAttempt(
                id=_new_id("ATT"),
                challenge_id=challenge_id,
                student_id=student_id,
                concept_answers=concept_answers,
                concept_correct=concept_correct,
                concept_total=concept_total,
                passed=runner_result["passed"],
                tests_passed=runner_result["tests_passed"],
                tests_total=runner_result["tests_total"],
                test_results=runner_result["test_results"],
                runtime_ms=runner_result["runtime_ms"],
                safe_error=runner_result["error"],
                submission_hash=submission_hash,
                created_at=completed,
            )
            data.setdefault("attempts", []).append(attempt.model_dump(mode="json"))
            persisted_challenge["attempt_count"] = int(persisted_challenge.get("attempt_count", 0)) + 1
            persisted_challenge["status"] = (
                ChallengeStatus.PASSED.value
                if attempt.passed
                else ChallengeStatus.FAILED.value
            )
            event_value = None
            passport_value = None
            if attempt.passed:
                event_id = _new_id("VER")
                evidence_snapshot = [
                    item
                    for item in data.get("evidence_items", [])
                    if item.get("id") in claim.get("evidence_ids", [])
                ]
                canonical = {
                    "id": event_id,
                    "student_id": student_id,
                    "claim_id": claim["id"],
                    "challenge_id": challenge_id,
                    "attempt_id": attempt.id,
                    "skill": claim["skill"],
                    "method": "proof_challenge",
                    "level": challenge["level"],
                    "passed": True,
                    "tests_passed": attempt.tests_passed,
                    "tests_total": attempt.tests_total,
                    "started_at": started.isoformat(),
                    "completed_at": completed.isoformat(),
                    "template_version": challenge["template_version"],
                    "submission_hash": submission_hash,
                    "evidence_snapshot": evidence_snapshot,
                }
                integrity_hash = hashlib.sha256(
                    json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                event = VerificationEvent(
                    **{key: value for key, value in canonical.items() if key != "evidence_snapshot"},
                    evidence_hash=integrity_hash,
                )
                event_value = event.model_dump(mode="json")
                data.setdefault("verification_events", []).append(event_value)
                claim.update(
                    {
                        "state": SkillState.CHALLENGE_VERIFIED.value,
                        "verified_level": challenge["level"],
                        "last_verified_at": completed.isoformat(),
                        "verification_event_id": event.id,
                    }
                )
                passport_value = build_passport(data, student_id)
            return {
                "attempt": attempt.model_dump(mode="json"),
                "verification_event": event_value,
                "claim": dict(claim),
                "passport": passport_value,
                "concept_check_note": "Concept answers are supporting information and never grant verification.",
            }

        return self.store.update(mutate)
