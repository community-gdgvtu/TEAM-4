"""Application orchestration while keeping trust decisions inside deterministic engines."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from backend.challenges.templates import get_template, public_template
from backend.core.config import Settings
from backend.engines.evidence_validation_engine import EvidenceValidationEngine
from backend.engines.opportunity_matching_engine import OpportunityMatchingEngine
from backend.engines.skill_claim_engine import SkillClaimEngine
from backend.models.schemas import (
    ChallengeAttempt,
    ChallengeStatus,
    EvidenceItem,
    Opportunity,
    ProofChallenge,
    SkillClaim,
    VerificationEvent,
)
from backend.services.academic_service import AcademicService
from backend.services.github_service import GitHubService, GitHubServiceError
from backend.services.passport_service import build_passport
from backend.services.persistence import Store, find_by_id, replace_for_student


class ApplicationService:
    def __init__(
        self,
        store: Store,
        settings: Settings,
        opportunity_engine: OpportunityMatchingEngine,
    ):
        self.store = store
        self.settings = settings
        self.opportunity_engine = opportunity_engine
        self.academic = AcademicService()
        self.github = GitHubService(settings.github_token)
        self.evidence_engine = EvidenceValidationEngine()
        self.claim_engine = SkillClaimEngine()
        self.ensure_demo_seeded()

    def ensure_demo_seeded(self) -> None:
        data = self.store.read()
        demo_claims = [item for item in data.get("claims", []) if item.get("student_id") == "STU-DEMO-IND-001"]
        if demo_claims and data.get("passports"):
            return
        self._derive_demo_state()

    def reset_demo(self) -> dict[str, Any]:
        self.store.reset()
        self._derive_demo_state()
        return self.dashboard("STU-DEMO-IND-001")

    def _derive_demo_state(self) -> None:
        data = self.store.read()
        student = find_by_id(data, "students", "STU-DEMO-IND-001")
        snapshot = next(item for item in data.get("repo_snapshots", []) if item.get("student_id") == student["id"])
        records = self.academic.records_for_student(data, student)
        evidence = self.evidence_engine.analyze(student, snapshot, records)
        preliminary = self.claim_engine.build(student["id"], evidence, [])
        python_claim = next(claim for claim in preliminary if claim.skill == "Python")
        prior = data["prior_verifications"][0]
        template = get_template(prior["template_id"])
        created = datetime.fromisoformat(prior["verified_at"].replace("Z", "+00:00"))
        public = public_template(template, include_demo_solution=True)
        challenge = ProofChallenge(
            id="CH-DEMO-PYTHON-PRIOR",
            student_id=student["id"],
            claim_id=python_claim.id,
            skill="Python",
            challenge_type=public["challenge_type"],
            level=prior["level"],
            template_id=template["template_id"],
            template_version=template["version"],
            title=template["title"],
            rationale=template["rationale"],
            source_context=[item.source_ref for item in evidence if item.skill == "Python"][:8],
            instructions=template["instructions"],
            starter_code=template["starter_code"],
            concept_questions=public["concept_questions"],
            public_tests=public["public_tests"],
            status=ChallengeStatus.PASSED,
            attempt_count=1,
            created_at=created,
            demo_solution=template["demo_solution"],
        )
        attempt = ChallengeAttempt(
            id="ATT-DEMO-PYTHON-PRIOR",
            challenge_id=challenge.id,
            student_id=student["id"],
            concept_answers={},
            passed=True,
            tests_passed=prior["tests_passed"],
            tests_total=prior["tests_total"],
            test_results=[],
            submission_hash=prior["submission_hash"],
            created_at=created,
        )
        canonical = {
            "student_id": student["id"], "claim_id": python_claim.id,
            "challenge_id": challenge.id, "skill": "Python", "level": prior["level"],
            "tests_passed": prior["tests_passed"], "tests_total": prior["tests_total"],
            "verified_at": prior["verified_at"], "submission_hash": prior["submission_hash"],
            "evidence_ids": python_claim.evidence_ids,
        }
        event = VerificationEvent(
            id="VER-DEMO-PYTHON-001",
            student_id=student["id"],
            claim_id=python_claim.id,
            challenge_id=challenge.id,
            attempt_id=attempt.id,
            skill="Python",
            level=prior["level"],
            passed=True,
            tests_passed=prior["tests_passed"],
            tests_total=prior["tests_total"],
            started_at=created,
            completed_at=created,
            template_version=template["version"],
            submission_hash=prior["submission_hash"],
            evidence_hash=hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        )
        claims = self.claim_engine.build(student["id"], evidence, [event])

        def mutate(current: dict[str, Any]) -> None:
            replace_for_student(current, "evidence_items", student["id"], [item.model_dump(mode="json") for item in evidence])
            replace_for_student(current, "claims", student["id"], [item.model_dump(mode="json") for item in claims])
            replace_for_student(current, "challenges", student["id"], [challenge.model_dump(mode="json")])
            replace_for_student(current, "attempts", student["id"], [attempt.model_dump(mode="json")])
            replace_for_student(current, "verification_events", student["id"], [event.model_dump(mode="json")])
            build_passport(current, student["id"])

        self.store.update(mutate)

    def analyze_evidence(
        self,
        student_id: str,
        repository_url: str | None,
        github_username: str | None,
        branch: str | None,
        use_demo_fallback: bool,
    ) -> dict[str, Any]:
        data = self.store.read()
        student = find_by_id(data, "students", student_id)
        if not student:
            raise KeyError("Student not found")
        fallback_used = False
        safe_message = None
        requested_url = repository_url or student.get("repository_url")
        demo_snapshot = next((item for item in data.get("repo_snapshots", []) if item.get("student_id") == "STU-DEMO-IND-001"), None)
        if student.get("demo") and (not repository_url or repository_url == student.get("repository_url")):
            snapshot = demo_snapshot
            fallback_used = True
            safe_message = "Using bounded offline demo GitHub snapshot."
        elif requested_url:
            try:
                snapshot = self.github.analyze(requested_url, github_username or student.get("github_username"), branch)
                snapshot["student_id"] = student_id
            except GitHubServiceError as exc:
                if not use_demo_fallback or not demo_snapshot:
                    raise
                snapshot = {**demo_snapshot, "student_id": student_id, "id": f"REPO-FALLBACK-{student_id}"}
                fallback_used = True
                safe_message = str(exc)
        elif use_demo_fallback and demo_snapshot:
            snapshot = {**demo_snapshot, "student_id": student_id, "id": f"REPO-FALLBACK-{student_id}"}
            fallback_used = True
            safe_message = "No repository configured; using bounded demo evidence."
        else:
            raise ValueError("Add a GitHub repository URL or enable demo fallback.")
        records = self.academic.records_for_student(data, student)
        evidence = self.evidence_engine.analyze(student, snapshot, records)
        events = [VerificationEvent.model_validate(item) for item in data.get("verification_events", []) if item.get("student_id") == student_id]
        claims = self.claim_engine.build(student_id, evidence, events)

        def mutate(current: dict[str, Any]) -> None:
            replace_for_student(current, "evidence_items", student_id, [item.model_dump(mode="json") for item in evidence])
            replace_for_student(current, "claims", student_id, [item.model_dump(mode="json") for item in claims])
            current["repo_snapshots"] = [item for item in current.get("repo_snapshots", []) if item.get("student_id") != student_id] + [snapshot]
            if any(claim.state.value == "CHALLENGE_VERIFIED" for claim in claims):
                build_passport(current, student_id)

        self.store.update(mutate)
        return {
            "student_id": student_id,
            "evidence_items": [item.model_dump(mode="json") for item in evidence],
            "claims": [item.model_dump(mode="json") for item in claims],
            "mode": "demo_snapshot" if fallback_used else "live_github",
            "message": safe_message,
        }

    def dashboard(self, student_id: str) -> dict[str, Any]:
        data = self.store.read()
        student = find_by_id(data, "students", student_id)
        if not student:
            raise KeyError("Student not found")
        evidence = [item for item in data.get("evidence_items", []) if item.get("student_id") == student_id]
        claims = [item for item in data.get("claims", []) if item.get("student_id") == student_id]
        return {
            "student": student,
            "stats": {
                "evidence_artifacts": len({(item["source_type"], item["source_ref"]) for item in evidence}),
                "skill_claims": len(claims),
                "evidence_backed": sum(item["state"] == "EVIDENCE_BACKED" for item in claims),
                "challenge_verified": sum(item["state"] == "CHALLENGE_VERIFIED" for item in claims),
            },
            "claims": claims,
            "demo_notice": data.get("demo_metadata", {}).get("notice"),
            "demo_context": {
                "reciprocal_context": data.get("demo_metadata", {}).get("reciprocal_context"),
                "institutions": data.get("institutions", []),
            },
            "persistence": self.store.backend_name,
        }

    def proofgraph(self, student_id: str) -> dict[str, Any]:
        data = self.store.read()
        student = find_by_id(data, "students", student_id)
        if not student:
            raise KeyError("Student not found")
        claims = [item for item in data.get("claims", []) if item.get("student_id") == student_id]
        evidence = [item for item in data.get("evidence_items", []) if item.get("student_id") == student_id]
        edges = [
            {"from": evidence_id, "to": claim["id"], "relationship": "SUPPORTS"}
            for claim in claims for evidence_id in claim.get("evidence_ids", [])
        ]
        return {"student_id": student_id, "student": student, "claims": claims, "evidence_items": evidence, "edges": edges}

    def opportunity_with_coverage(self, opportunity: Opportunity, student_id: str | None) -> dict[str, Any]:
        if not student_id:
            return opportunity.model_dump(mode="json")
        data = self.store.read()
        if not find_by_id(data, "students", student_id):
            raise KeyError("Student not found")
        claims = [item for item in data.get("claims", []) if item.get("student_id") == student_id]
        return self.opportunity_engine.match(opportunity, claims).model_dump(mode="json")
