"""Issue portable, inspectable skill stamps from persisted verification events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.engines.evidence_validation_engine import stable_id
from backend.models.schemas import Passport, SkillStamp, SkillState
from backend.services.persistence import Store, find_by_id


def build_passport(data: dict[str, Any], student_id: str) -> dict[str, Any]:
    student = find_by_id(data, "students", student_id)
    if not student:
        raise KeyError("Student not found")
    now = datetime.now(timezone.utc)
    claims = [
        claim
        for claim in data.get("claims", [])
        if claim.get("student_id") == student_id
        and claim.get("state") == SkillState.CHALLENGE_VERIFIED.value
    ]
    evidence = {item["id"]: item for item in data.get("evidence_items", [])}
    events = {item["id"]: item for item in data.get("verification_events", [])}
    stamps: list[SkillStamp] = []
    for claim in claims:
        event = events.get(claim.get("verification_event_id"))
        if not event or not event.get("passed"):
            continue
        sources = sorted(
            {
                evidence[item_id]["source_type"]
                for item_id in claim.get("evidence_ids", [])
                if item_id in evidence
            }
        )
        verified_at = datetime.fromisoformat(str(event["completed_at"]).replace("Z", "+00:00"))
        age_days = max(0, (now - verified_at).days)
        freshness = (
            "Fresh — verified today"
            if age_days == 0
            else f"Fresh — verified {age_days} days ago"
            if age_days <= 90
            else f"Review recommended — verified {age_days} days ago"
        )
        stamps.append(
            SkillStamp(
                skill=claim["skill"],
                trust_state=SkillState.CHALLENGE_VERIFIED,
                verified_level=event["level"],
                evidence_sources=sources,
                verification_method="Repo-grounded deterministic proof challenge",
                verification_date=event["completed_at"],
                verification_event_id=event["id"],
                freshness=freshness,
                integrity_hash=event["evidence_hash"],
            )
        )
    existing = next(
        (item for item in data.get("passports", []) if item.get("student_id") == student_id),
        None,
    )
    passport_id = (
        existing["id"]
        if existing
        else "PASS-DEMO-001"
        if student.get("demo")
        else stable_id("PASS", student_id)
    )
    passport = Passport(
        id=passport_id,
        student_id=student_id,
        candidate_display_name=student["display_name"],
        headline=student.get("headline") or student.get("study_area", "SkillPassport"),
        issued_at=(existing.get("issued_at") if existing else now),
        updated_at=now,
        stamps=sorted(stamps, key=lambda item: item.skill),
    ).model_dump(mode="json")
    data["passports"] = [
        item for item in data.get("passports", []) if item.get("student_id") != student_id
    ] + [passport]
    return passport


class PassportService:
    def __init__(self, store: Store):
        self.store = store

    def issue(self, student_id: str) -> Passport:
        value = self.store.update(lambda data: build_passport(data, student_id))
        return Passport.model_validate(value)

    def get_for_student(self, student_id: str) -> Passport | None:
        data = self.store.read()
        item = next(
            (item for item in data.get("passports", []) if item.get("student_id") == student_id),
            None,
        )
        return Passport.model_validate(item) if item else None

    def get_public(self, passport_id: str) -> Passport | None:
        item = find_by_id(self.store.read(), "passports", passport_id)
        return Passport.model_validate(item) if item else None
