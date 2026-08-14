"""Transparent requirement parsing and claim-state comparison."""

from __future__ import annotations

import re
from typing import Any

from backend.core.taxonomy import SKILLS
from backend.engines.evidence_validation_engine import stable_id
from backend.models.schemas import (
    Opportunity,
    OpportunityCoverage,
    OpportunityRequirement,
    RequirementImportance,
    RequirementMatch,
    RequirementState,
    SkillState,
)
from backend.services.gemini_service import GeminiService


class OpportunityMatchingEngine:
    def __init__(self, gemini: GeminiService):
        self.gemini = gemini

    def parse(
        self, title: str, company: str, country: str, description: str
    ) -> Opportunity:
        gemini_value = self.gemini.extract_opportunity(description)
        requirements: list[OpportunityRequirement] = []
        if gemini_value:
            requirements = [
                OpportunityRequirement(
                    skill=item.skill,
                    importance=item.importance,
                    source_text=item.source_text,
                )
                for item in gemini_value.requirements
            ]
        else:
            lowered = description.lower()
            for skill, definition in SKILLS.items():
                aliases = (skill, *definition.aliases)
                matched = next(
                    (
                        alias
                        for alias in aliases
                        if (alias.lower() in lowered if any(ord(ch) > 127 for ch in alias) else re.search(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", lowered))
                    ),
                    None,
                )
                if not matched:
                    continue
                clauses = [part.strip() for part in re.split(r"[。;\n]+|(?<=[.!?])\s+", description) if part.strip()]
                context = next((part for part in clauses if matched.lower() in part.lower()), description)
                context_lower = context.lower()
                required = any(word in context_lower for word in ("required", "must", "必須"))
                preferred = not required and any(word in context_lower for word in ("preferred", "nice to have", "歓迎", "尚可", "望ましい"))
                requirements.append(
                    OpportunityRequirement(
                        skill=skill,
                        importance=(RequirementImportance.PREFERRED if preferred else RequirementImportance.REQUIRED),
                        source_text=context.strip(),
                    )
                )
        if not requirements:
            raise ValueError("Describe at least one recognizable capability requirement.")
        language = "Japanese or mixed" if any(ord(char) > 127 for char in description) else "English"
        return Opportunity(
            id=stable_id("OPP", title, company, description),
            title=title,
            company=company,
            country=country,
            description=description,
            original_language=language,
            requirements=requirements,
        )

    def match(
        self, opportunity: Opportunity, claims: list[dict[str, Any]]
    ) -> OpportunityCoverage:
        by_skill = {claim["skill"].lower(): claim for claim in claims}
        matches: list[RequirementMatch] = []
        for requirement in opportunity.requirements:
            claim = by_skill.get(requirement.skill.lower())
            if not claim:
                state = RequirementState.MISSING
                reason = "No inspectable evidence currently supports this requirement."
            else:
                state = RequirementState(claim["state"])
                reason = {
                    SkillState.CHALLENGE_VERIFIED.value: "A deterministic proof challenge has passed for this claim.",
                    SkillState.EVIDENCE_BACKED.value: "Multiple inspectable signals support this claim; execution is not yet verified.",
                    SkillState.DETECTED.value: "A signal exists, but corroborating proof is still limited.",
                }[claim["state"]]
            matches.append(
                RequirementMatch(
                    requirement=requirement,
                    state=state,
                    matched_claim_id=(claim["id"] if claim else None),
                    reason=reason,
                    action_available=bool(claim and claim.get("challenge_available") and state != RequirementState.CHALLENGE_VERIFIED),
                )
            )
        required = [item for item in matches if item.requirement.importance == RequirementImportance.REQUIRED]
        count = lambda state: sum(item.state == state for item in required)
        verified = count(RequirementState.CHALLENGE_VERIFIED)
        backed = count(RequirementState.EVIDENCE_BACKED)
        missing = count(RequirementState.MISSING)
        detected = count(RequirementState.DETECTED)
        return OpportunityCoverage(
            opportunity=opportunity,
            matches=matches,
            required_total=len(required),
            required_challenge_verified=verified,
            required_evidence_backed=backed,
            required_detected=detected,
            required_missing=missing,
            preferred_total=len(matches) - len(required),
            explanation=f"{verified} of {len(required)} required capabilities are challenge-verified; {backed} are evidence-backed; {detected} are detected; {missing} are missing.",
        )
