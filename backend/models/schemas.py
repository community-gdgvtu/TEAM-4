"""Typed contracts shared by the SkillPassport API and trust engines."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SkillState(str, Enum):
    DETECTED = "DETECTED"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    CHALLENGE_VERIFIED = "CHALLENGE_VERIFIED"


class EvidenceStrength(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class EvidenceSourceType(str, Enum):
    GITHUB_CODE = "GITHUB_CODE"
    GITHUB_DEPENDENCY = "GITHUB_DEPENDENCY"
    GITHUB_TEST = "GITHUB_TEST"
    GITHUB_COMMIT = "GITHUB_COMMIT"
    ACADEMIC = "ACADEMIC"
    PRIOR_VERIFICATION = "PRIOR_VERIFICATION"


class EvidenceDirectness(str, Enum):
    DIRECT = "DIRECT"
    CORROBORATING = "CORROBORATING"
    CONTEXTUAL = "CONTEXTUAL"


class ChallengeType(str, Enum):
    PYTHON_FUNCTION = "PYTHON_FUNCTION"
    FASTAPI_VALIDATION = "FASTAPI_VALIDATION"
    SQL_QUERY = "SQL_QUERY"


class ChallengeLevel(str, Enum):
    FOUNDATION = "FOUNDATION"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class ChallengeStatus(str, Enum):
    READY = "READY"
    PASSED = "PASSED"
    FAILED = "FAILED"


class RequirementImportance(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"


class RequirementState(str, Enum):
    CHALLENGE_VERIFIED = "CHALLENGE_VERIFIED"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    DETECTED = "DETECTED"
    MISSING = "MISSING"


class EvidenceItem(DomainModel):
    id: str
    student_id: str
    source_type: EvidenceSourceType
    skill: str
    title: str
    source_ref: str
    directness: EvidenceDirectness
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SkillClaim(DomainModel):
    id: str
    student_id: str
    skill: str
    state: SkillState
    evidence_strength: EvidenceStrength
    evidence_ids: list[str]
    uncertainties: list[str] = Field(default_factory=list)
    challenge_available: bool = False
    verified_level: ChallengeLevel | None = None
    last_verified_at: datetime | None = None
    verification_event_id: str | None = None


class ConceptQuestion(DomainModel):
    id: str
    prompt: str
    options: list[str]


class PublicTest(DomainModel):
    name: str
    description: str


class ProofChallenge(DomainModel):
    id: str
    student_id: str
    claim_id: str
    skill: str
    challenge_type: ChallengeType
    level: ChallengeLevel
    template_id: str
    template_version: str
    title: str
    rationale: str
    source_context: list[str] = Field(default_factory=list)
    instructions: str
    starter_code: str
    concept_questions: list[ConceptQuestion] = Field(default_factory=list)
    public_tests: list[PublicTest] = Field(default_factory=list)
    status: ChallengeStatus = ChallengeStatus.READY
    attempt_count: int = 0
    created_at: datetime
    demo_solution: str | None = None


class TestResult(DomainModel):
    name: str
    passed: bool
    detail: str


class ChallengeAttempt(DomainModel):
    id: str
    challenge_id: str
    student_id: str
    concept_answers: dict[str, int] = Field(default_factory=dict)
    concept_correct: int = 0
    concept_total: int = 0
    passed: bool
    tests_passed: int
    tests_total: int
    test_results: list[TestResult] = Field(default_factory=list)
    runtime_ms: int = 0
    safe_error: str | None = None
    submission_hash: str
    created_at: datetime


class VerificationEvent(DomainModel):
    id: str
    student_id: str
    claim_id: str
    challenge_id: str
    attempt_id: str
    skill: str
    method: str = "proof_challenge"
    level: ChallengeLevel
    passed: bool
    tests_passed: int
    tests_total: int
    started_at: datetime
    completed_at: datetime
    template_version: str
    submission_hash: str
    evidence_hash: str


class OpportunityRequirement(DomainModel):
    skill: str
    importance: RequirementImportance = RequirementImportance.REQUIRED
    level: ChallengeLevel | None = None
    source_text: str


class RequirementMatch(DomainModel):
    requirement: OpportunityRequirement
    state: RequirementState
    matched_claim_id: str | None = None
    reason: str
    action_available: bool = False


class Opportunity(DomainModel):
    id: str
    title: str
    company: str
    country: str
    description: str
    original_language: str = "English"
    requirements: list[OpportunityRequirement]
    demo: bool = False


class OpportunityCoverage(DomainModel):
    opportunity: Opportunity
    matches: list[RequirementMatch]
    required_total: int
    required_challenge_verified: int
    required_evidence_backed: int
    required_detected: int
    required_missing: int
    preferred_total: int
    explanation: str


class SkillStamp(DomainModel):
    skill: str
    trust_state: SkillState
    verified_level: ChallengeLevel
    evidence_sources: list[str]
    verification_method: str
    verification_date: datetime
    verification_event_id: str
    freshness: str
    integrity_hash: str


class Passport(DomainModel):
    id: str
    student_id: str
    candidate_display_name: str
    headline: str
    issued_at: datetime
    updated_at: datetime
    stamps: list[SkillStamp] = Field(default_factory=list)


class ManualCoursework(DomainModel):
    course_name: str = Field(min_length=2, max_length=160)
    grade: str = Field(min_length=1, max_length=20)
    skills: list[str] = Field(min_length=1, max_length=8)


class SignupRequest(DomainModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=256)
    institution: str = Field(min_length=2, max_length=160)
    country: str = Field(min_length=2, max_length=80)
    study_area: str = Field(min_length=2, max_length=120)
    github_username: str | None = Field(default=None, max_length=80)
    repository_url: str | None = Field(default=None, max_length=300)
    academic_source: Literal["demo", "manual"] = "demo"
    manual_coursework: list[ManualCoursework] = Field(default_factory=list, max_length=20)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(DomainModel):
    email: str
    password: str


class EvidenceAnalyzeRequest(DomainModel):
    student_id: str
    repository_url: str | None = None
    github_username: str | None = None
    branch: str | None = None
    use_demo_fallback: bool = True


class ChallengeCreateRequest(DomainModel):
    student_id: str
    claim_id: str


class ChallengeSubmitRequest(DomainModel):
    student_id: str
    concept_answers: dict[str, int] = Field(default_factory=dict)
    solution: str = Field(min_length=1, max_length=20_000)


class OpportunityAnalyzeRequest(DomainModel):
    student_id: str
    description: str = Field(min_length=20, max_length=20_000)
    title: str = Field(default="Pasted opportunity", max_length=160)
    company: str = Field(default="Opportunity", max_length=160)
    country: str = Field(default="Japan / India", max_length=80)
