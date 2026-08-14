"""Optional structured Gemini interpretation. It never verifies a skill."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.core.config import Settings
from backend.core.taxonomy import SKILLS, normalize_skill


class ExtractedRequirement(BaseModel):
    skill: str
    importance: Literal["REQUIRED", "PREFERRED"]
    source_text: str


class ExtractedOpportunity(BaseModel):
    requirements: list[ExtractedRequirement] = Field(max_length=20)
    explanation: str = Field(max_length=500)


class ChallengePersonalization(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    rationale: str = Field(min_length=10, max_length=500)
    instructions: str = Field(min_length=20, max_length=1500)


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def extract_opportunity(self, description: str) -> ExtractedOpportunity | None:
        if not self.settings.gemini_api_key:
            return None
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.settings.gemini_api_key)
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=(
                    "Extract only explicit capability requirements from this opportunity. "
                    f"Normalize skills to this allowlist: {', '.join(SKILLS)}. "
                    "Do not infer verification or candidate ability.\n\n" + description
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedOpportunity,
                ),
            )
            parsed = response.parsed or ExtractedOpportunity.model_validate_json(response.text)
            normalized = []
            for requirement in parsed.requirements:
                skill = normalize_skill(requirement.skill)
                if skill:
                    normalized.append(requirement.model_copy(update={"skill": skill}))
            return parsed.model_copy(update={"requirements": normalized}) if normalized else None
        except Exception:
            return None

    def personalize_challenge(
        self,
        *,
        skill: str,
        source_context: list[str],
        title: str,
        rationale: str,
        instructions: str,
    ) -> ChallengePersonalization | None:
        """Personalize wording only; verifier template and tests are immutable."""
        if not self.settings.gemini_api_key:
            return None
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.settings.gemini_api_key)
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=(
                    "Personalize only the title, rationale, and instructions for a fixed "
                    "SkillPassport proof challenge. Do not add commands, imports, tests, "
                    "pass criteria, or claims of verification. Preserve the requested function/query contract.\n"
                    f"Skill: {skill}\nEvidence paths: {source_context[:8]}\n"
                    f"Base title: {title}\nBase rationale: {rationale}\nBase instructions: {instructions}"
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChallengePersonalization,
                ),
            )
            return response.parsed or ChallengePersonalization.model_validate_json(response.text)
        except Exception:
            return None
