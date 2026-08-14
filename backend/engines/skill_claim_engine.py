"""Explainable skill lifecycle derived from evidence and verification events."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from backend.core.taxonomy import SKILLS, challenge_supported
from backend.engines.evidence_validation_engine import stable_id
from backend.models.schemas import (
    ChallengeLevel,
    EvidenceDirectness,
    EvidenceItem,
    EvidenceSourceType,
    EvidenceStrength,
    SkillClaim,
    SkillState,
    VerificationEvent,
)


class SkillClaimEngine:
    def build(
        self,
        student_id: str,
        evidence_items: Iterable[EvidenceItem],
        verification_events: Iterable[VerificationEvent],
    ) -> list[SkillClaim]:
        grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in evidence_items:
            grouped[item.skill].append(item)

        passed_events: dict[str, VerificationEvent] = {}
        for event in verification_events:
            if event.student_id == student_id and event.passed:
                current = passed_events.get(event.skill)
                if current is None or event.completed_at > current.completed_at:
                    passed_events[event.skill] = event

        claims: list[SkillClaim] = []
        for skill in sorted(grouped):
            items = grouped[skill]
            direct = [item for item in items if item.directness == EvidenceDirectness.DIRECT]
            corroborating = [
                item for item in items if item.directness == EvidenceDirectness.CORROBORATING
            ]
            independent_refs = {item.source_ref for item in direct + corroborating}
            source_types = {item.source_type for item in direct + corroborating}

            backed = bool(direct) and len(direct) + len(corroborating) >= 2 and (
                len(independent_refs) >= 2 or len(source_types) >= 2
            )
            if backed and (len(direct) >= 2 and len(corroborating) >= 2):
                strength = EvidenceStrength.STRONG
            elif backed:
                strength = EvidenceStrength.MODERATE
            else:
                strength = EvidenceStrength.WEAK

            event = passed_events.get(skill)
            state = (
                SkillState.CHALLENGE_VERIFIED
                if event
                else SkillState.EVIDENCE_BACKED
                if backed
                else SkillState.DETECTED
            )
            definition = SKILLS.get(skill)
            claims.append(
                SkillClaim(
                    id=stable_id("CLM", student_id, skill),
                    student_id=student_id,
                    skill=skill,
                    state=state,
                    evidence_strength=strength,
                    evidence_ids=[item.id for item in items],
                    uncertainties=(list(definition.uncertainties) if definition else []),
                    challenge_available=challenge_supported(skill),
                    verified_level=(ChallengeLevel(event.level) if event else None),
                    last_verified_at=(event.completed_at if event else None),
                    verification_event_id=(event.id if event else None),
                )
            )
        return claims

