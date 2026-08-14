"""SkillPassport HTTP API. Browser state is never a verification authority."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request, Response

from backend.core.config import get_settings
from backend.engines.opportunity_matching_engine import OpportunityMatchingEngine
from backend.engines.proof_verification_engine import ProofVerificationEngine
from backend.models.schemas import (
    ChallengeCreateRequest,
    ChallengeSubmitRequest,
    EvidenceAnalyzeRequest,
    LoginRequest,
    Opportunity,
    OpportunityAnalyzeRequest,
    SignupRequest,
)
from backend.services.application import ApplicationService
from backend.services.auth_service import AuthService
from backend.services.gemini_service import GeminiService
from backend.services.github_service import GitHubServiceError
from backend.services.passport_service import PassportService
from backend.services.persistence import create_store, find_by_id

router = APIRouter()
settings = get_settings()
store = create_store(settings)
gemini = GeminiService(settings)
opportunity_engine = OpportunityMatchingEngine(gemini)
application = ApplicationService(store, settings, opportunity_engine)
auth = AuthService(store)
proof = ProofVerificationEngine(store, settings)
passports = PassportService(store)


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


@router.get("/health")
def health() -> dict[str, Any]:
    try:
        store.read()
    except Exception:
        raise HTTPException(status_code=503, detail="Persistence is unavailable") from None
    return {
        "status": "ok",
        "service": "SkillPassport",
        "persistence": store.backend_name,
        "persistence_durability": (
            "durable_mongodb"
            if store.backend_name == "mongodb"
            else "ephemeral_render_fallback"
            if settings.is_render
            else "local_atomic_json"
        ),
        "cors_origins": list(settings.cors_origins),
        "runtime": "render" if settings.is_render else "local",
        "github_live_available": True,
        "gemini_mode": "structured_optional" if gemini.available else "deterministic_fallback",
        "verification_authority": "deterministic_proof_engine",
    }


@router.post("/auth/signup", status_code=201)
def signup(request: SignupRequest) -> dict[str, Any]:
    try:
        return auth.signup(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    try:
        return auth.login(request)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid email or password") from None


@router.post("/demo/reset")
def reset_demo() -> dict[str, Any]:
    value = application.reset_demo()
    return {
        "status": "reset",
        "student_id": value["student"]["id"],
        "student": value["student"],
        "dashboard": value,
    }


@router.get("/students/{student_id}/dashboard")
def dashboard(student_id: str) -> dict[str, Any]:
    try:
        return application.dashboard(student_id)
    except KeyError:
        raise not_found("Student not found") from None


@router.post("/evidence/analyze")
def analyze_evidence(request: EvidenceAnalyzeRequest) -> dict[str, Any]:
    try:
        return application.analyze_evidence(
            request.student_id,
            request.repository_url,
            request.github_username,
            request.branch,
            request.use_demo_fallback,
        )
    except KeyError:
        raise not_found("Student not found") from None
    except (ValueError, GitHubServiceError) as exc:
        raise bad_request(str(exc)) from None


@router.get("/students/{student_id}/proofgraph")
def proofgraph(student_id: str) -> dict[str, Any]:
    try:
        return application.proofgraph(student_id)
    except KeyError:
        raise not_found("Student not found") from None


@router.get("/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    data = store.read()
    claim = find_by_id(data, "claims", claim_id)
    if not claim:
        raise not_found("Skill claim not found")
    evidence = {item["id"]: item for item in data.get("evidence_items", [])}
    event = find_by_id(data, "verification_events", claim.get("verification_event_id", ""))
    return {
        "claim": claim,
        "evidence_items": [evidence[item_id] for item_id in claim.get("evidence_ids", []) if item_id in evidence],
        "verification_event": event,
    }


@router.post("/challenges", status_code=201)
def create_challenge(request: ChallengeCreateRequest) -> dict[str, Any]:
    try:
        return proof.create_challenge(request.student_id, request.claim_id).model_dump(mode="json")
    except KeyError:
        raise not_found("Skill claim not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: str) -> dict[str, Any]:
    challenge = proof.get_challenge(challenge_id)
    if not challenge:
        raise not_found("Proof challenge not found")
    return challenge.model_dump(mode="json")


@router.post("/challenges/{challenge_id}/submit")
def submit_challenge(challenge_id: str, request: ChallengeSubmitRequest) -> dict[str, Any]:
    try:
        return proof.submit(
            challenge_id,
            request.student_id,
            request.concept_answers,
            request.solution,
        )
    except KeyError:
        raise not_found("Proof challenge not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/opportunities")
def list_opportunities(student_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    data = store.read()
    values = [Opportunity.model_validate(item) for item in data.get("opportunities", [])]
    try:
        return [application.opportunity_with_coverage(item, student_id) for item in values]
    except KeyError:
        raise not_found("Student not found") from None


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: str, student_id: str | None = Query(default=None)
) -> dict[str, Any]:
    item = find_by_id(store.read(), "opportunities", opportunity_id)
    if not item:
        raise not_found("Opportunity not found")
    try:
        return application.opportunity_with_coverage(Opportunity.model_validate(item), student_id)
    except KeyError:
        raise not_found("Student not found") from None


@router.post("/opportunities/analyze", status_code=201)
def analyze_opportunity(request: OpportunityAnalyzeRequest) -> dict[str, Any]:
    try:
        opportunity = opportunity_engine.parse(
            request.title, request.company, request.country, request.description
        )
        store.update(
            lambda data: data.setdefault("opportunities", []).append(
                opportunity.model_dump(mode="json")
            )
        )
        return application.opportunity_with_coverage(opportunity, request.student_id)
    except KeyError:
        raise not_found("Student not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/jobs")
def jobs_compatibility() -> list[dict[str, Any]]:
    """Compatibility alias while the old frontend migrates to Opportunity Lens."""
    values = []
    for item in store.read().get("opportunities", []):
        required = [req["skill"] for req in item.get("requirements", [])]
        values.append(
            {
                **item,
                "job_id": item["id"],
                "job_title": item["title"],
                "required_skills": ", ".join(required),
            }
        )
    return values


@router.get("/students/{student_id}/passport")
def get_passport(student_id: str) -> dict[str, Any]:
    if not find_by_id(store.read(), "students", student_id):
        raise not_found("Student not found")
    value = passports.get_for_student(student_id) or passports.issue(student_id)
    return value.model_dump(mode="json")


@router.post("/students/{student_id}/passport", status_code=201)
def issue_passport(student_id: str) -> dict[str, Any]:
    try:
        return passports.issue(student_id).model_dump(mode="json")
    except KeyError:
        raise not_found("Student not found") from None


@router.post("/students/{student_id}/passport/issue", status_code=201)
def issue_passport_alias(student_id: str) -> dict[str, Any]:
    return issue_passport(student_id)


@router.get("/public/passports/{passport_id}")
def public_passport(passport_id: str) -> dict[str, Any]:
    value = passports.get_public(passport_id)
    if not value:
        raise not_found("Passport not found")
    return value.model_dump(mode="json")


@router.get("/public/passports/{passport_id}/qr.png")
def passport_qr(
    passport_id: str,
    request: Request,
    origin: str | None = Query(default=None, max_length=300),
) -> Response:
    if not passports.get_public(passport_id):
        raise not_found("Passport not found")
    candidate_origin = (
        settings.public_base_url
        or origin
        or (settings.cors_origins[0] if settings.cors_origins else None)
        or str(request.base_url).rstrip("/")
    )
    parsed = urlparse(candidate_origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise bad_request("Origin must be an HTTP(S) URL")
    normalized_origin = f"{parsed.scheme}://{parsed.netloc}"
    if (
        origin
        and not settings.public_base_url
        and settings.cors_origins
        and normalized_origin not in settings.cors_origins
    ):
        raise bad_request("Origin is not an allowed frontend URL")
    public_url = f"{normalized_origin}/#/verify/{passport_id}"
    try:
        import qrcode
    except ImportError:
        raise HTTPException(status_code=503, detail="QR support is unavailable") from None
    image = qrcode.make(public_url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})
