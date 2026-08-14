from __future__ import annotations

import builtins
import importlib
import json
import sys
import types

import pytest
from fastapi.testclient import TestClient

from backend.models.schemas import SkillState


STUDENT_ID = "STU-DEMO-IND-001"
TOKYO_OPPORTUNITY_ID = "OPP-TOKYO-BACKEND-001"


@pytest.fixture
def api(tmp_path, fixture_path, monkeypatch):
    monkeypatch.setenv("SKILLPASSPORT_STORE_PATH", str(tmp_path / "api-runtime.json"))
    monkeypatch.setenv("CHALLENGE_TIMEOUT_SECONDS", "1")
    for variable in ("GEMINI_API_KEY", "GITHUB_TOKEN", "MONGODB_URI", "PUBLIC_BASE_URL"):
        monkeypatch.delenv(variable, raising=False)

    # The application intentionally owns one process-global store. Reload its two
    # composition modules only, after configuring an isolated path for this test.
    sys.modules.pop("backend.main", None)
    sys.modules.pop("backend.api.routes", None)
    routes = importlib.import_module("backend.api.routes")
    main = importlib.import_module("backend.main")
    with TestClient(main.app) as client:
        yield client, routes
    sys.modules.pop("backend.main", None)
    sys.modules.pop("backend.api.routes", None)


def _claims_by_skill(payload: dict) -> dict[str, dict]:
    return {claim["skill"]: claim for claim in payload["claims"]}


def test_health_and_one_process_frontend(api):
    client, _ = api

    health = client.get("/api/health")
    landing = client.get("/")
    stylesheet = client.get("/styles.css")
    javascript = client.get("/app.js")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["gemini_mode"] == "deterministic_fallback"
    assert health.json()["verification_authority"] == "deterministic_proof_engine"
    assert landing.status_code == 200
    assert "SkillPassport" in landing.text
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert ":root" in stylesheet.text
    assert javascript.status_code == 200
    assert "javascript" in javascript.headers["content-type"]
    assert 'const API_BASE = normalizeRuntimeBase(runtimeConfig.apiBase, "/api")' in javascript.text
    assert client.get(f"/api/students/{STUDENT_ID}/dashboard").status_code == 200
    assert client.get("/api/opportunities").status_code == 200
    assert client.get("/api/jobs").status_code == 200


def test_demo_reset_is_api_idempotent(api):
    client, _ = api

    first = client.post("/api/demo/reset")
    second = client.post("/api/demo/reset")

    assert first.status_code == 200
    assert second.status_code == 200
    first_dashboard = first.json()["dashboard"]
    second_dashboard = second.json()["dashboard"]
    assert first_dashboard["student"]["id"] == STUDENT_ID
    assert first_dashboard["stats"] == second_dashboard["stats"]
    assert {
        skill: (claim["id"], claim["state"])
        for skill, claim in _claims_by_skill(first_dashboard).items()
    } == {
        skill: (claim["id"], claim["state"])
        for skill, claim in _claims_by_skill(second_dashboard).items()
    }
    assert _claims_by_skill(second_dashboard)["FastAPI"]["state"] == SkillState.EVIDENCE_BACKED.value


def test_api_evidence_proof_challenge_opportunity_passport_public_loop(api):
    client, _ = api
    assert client.post("/api/demo/reset").status_code == 200

    analyzed = client.post(
        "/api/evidence/analyze",
        json={"student_id": STUDENT_ID, "use_demo_fallback": True},
    )
    assert analyzed.status_code == 200
    assert analyzed.json()["mode"] == "demo_snapshot"
    claims = _claims_by_skill(analyzed.json())
    fastapi_claim = claims["FastAPI"]
    assert fastapi_claim["state"] == SkillState.EVIDENCE_BACKED.value

    graph = client.get(f"/api/students/{STUDENT_ID}/proofgraph")
    assert graph.status_code == 200
    assert graph.json()["edges"]
    assert any(
        item["source_ref"] == "app/routes/users.py"
        for item in graph.json()["evidence_items"]
    )

    claim_response = client.get(f"/api/claims/{fastapi_claim['id']}")
    assert claim_response.status_code == 200
    assert claim_response.json()["verification_event"] is None
    assert claim_response.json()["evidence_items"]

    before = client.get(
        f"/api/opportunities/{TOKYO_OPPORTUNITY_ID}",
        params={"student_id": STUDENT_ID},
    )
    assert before.status_code == 200
    before_fastapi = next(
        item for item in before.json()["matches"] if item["requirement"]["skill"] == "FastAPI"
    )
    assert before_fastapi["state"] == "EVIDENCE_BACKED"
    assert before_fastapi["action_available"] is True

    created = client.post(
        "/api/challenges",
        json={"student_id": STUDENT_ID, "claim_id": fastapi_claim["id"]},
    )
    assert created.status_code == 201
    challenge = created.json()
    challenge_id = challenge["id"]
    assert challenge["skill"] == "FastAPI"
    assert challenge["demo_solution"]
    assert all("correct" not in question for question in challenge["concept_questions"])
    assert client.get(f"/api/challenges/{challenge_id}").status_code == 200

    failed = client.post(
        f"/api/challenges/{challenge_id}/submit",
        json={
            "student_id": STUDENT_ID,
            "concept_answers": {"api-q1": 1, "api-q2": 1},
            "solution": "def create_user(payload, users):\n    return {'status_code': 201, 'body': payload}\n",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["attempt"]["passed"] is False
    assert failed.json()["attempt"]["concept_correct"] == 2
    assert failed.json()["verification_event"] is None
    after_failure = client.get(f"/api/claims/{fastapi_claim['id']}").json()
    assert after_failure["claim"]["state"] == SkillState.EVIDENCE_BACKED.value
    assert after_failure["verification_event"] is None

    passed = client.post(
        f"/api/challenges/{challenge_id}/submit",
        json={
            "student_id": STUDENT_ID,
            "concept_answers": {},
            "solution": challenge["demo_solution"],
        },
    )
    assert passed.status_code == 200
    assert passed.json()["attempt"]["passed"] is True
    event = passed.json()["verification_event"]
    assert event["passed"] is True
    assert len(event["evidence_hash"]) == 64
    assert passed.json()["claim"]["state"] == SkillState.CHALLENGE_VERIFIED.value

    reanalyzed = client.post(
        "/api/evidence/analyze",
        json={"student_id": STUDENT_ID, "use_demo_fallback": True},
    )
    assert reanalyzed.status_code == 200
    assert _claims_by_skill(reanalyzed.json())["FastAPI"]["state"] == SkillState.CHALLENGE_VERIFIED.value

    after = client.get(
        f"/api/opportunities/{TOKYO_OPPORTUNITY_ID}",
        params={"student_id": STUDENT_ID},
    )
    assert after.status_code == 200
    after_fastapi = next(
        item for item in after.json()["matches"] if item["requirement"]["skill"] == "FastAPI"
    )
    assert after_fastapi["state"] == "CHALLENGE_VERIFIED"
    assert after_fastapi["action_available"] is False

    passport_response = client.get(f"/api/students/{STUDENT_ID}/passport")
    assert passport_response.status_code == 200
    passport = passport_response.json()
    assert any(
        stamp["verification_event_id"] == event["id"] for stamp in passport["stamps"]
    )

    public = client.get(f"/api/public/passports/{passport['id']}")
    assert public.status_code == 200
    assert public.json() == passport
    assert "email" not in json.dumps(public.json()).lower()

    issued = client.post(f"/api/students/{STUDENT_ID}/passport/issue")
    assert issued.status_code == 201
    assert issued.json()["id"] == passport["id"]
    invalid_qr = client.get(
        f"/api/public/passports/{passport['id']}/qr.png",
        params={"origin": "javascript:alert(1)"},
    )
    assert invalid_qr.status_code == 400


def test_api_opportunity_analysis_uses_no_key_fallback(api):
    client, _ = api
    client.post("/api/demo/reset")
    response = client.post(
        "/api/opportunities/analyze",
        json={
            "student_id": STUDENT_ID,
            "title": "Bilingual Backend Internship",
            "company": "Fictional Company",
            "country": "Japan",
            "description": (
                "Python, FastAPI, and SQL are required for this internship. "
                "Docker is preferred."
            ),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    requirements = {
        item["requirement"]["skill"]: item["requirement"]["importance"]
        for item in payload["matches"]
    }
    assert requirements == {
        "Python": "REQUIRED",
        "FastAPI": "REQUIRED",
        "SQL": "REQUIRED",
        "Docker": "PREFERRED",
    }
    assert payload["required_total"] == 3


def test_api_signup_login_and_persisted_secret_redaction(api):
    client, routes = api
    password = "api plaintext sentinel password"
    signup = client.post(
        "/api/auth/signup",
        json={
            "name": "API Candidate",
            "email": "api-candidate@example.test",
            "password": password,
            "institution": "Example Institute",
            "country": "India",
            "study_area": "Computer Science",
            "academic_source": "manual",
            "manual_coursework": [
                {"course_name": "Database Systems", "grade": "A", "skills": ["SQL"]}
            ],
        },
    )
    assert signup.status_code == 201
    assert password not in json.dumps(signup.json())

    login = client.post(
        "/api/auth/login",
        json={"email": "api-candidate@example.test", "password": password},
    )
    rejected = client.post(
        "/api/auth/login",
        json={"email": "api-candidate@example.test", "password": "wrong password"},
    )

    assert login.status_code == 200
    assert rejected.status_code == 401
    serialized = json.dumps(routes.store.read(), sort_keys=True)
    assert password not in serialized
    assert signup.json()["token"] not in serialized


def test_qr_route_returns_png_and_encodes_the_public_route_when_support_exists(
    api, monkeypatch
):
    client, _ = api
    captured: dict[str, str] = {}
    fake_qrcode = types.ModuleType("qrcode")

    class FakeImage:
        def save(self, buffer, format):
            assert format == "PNG"
            buffer.write(b"\x89PNG\r\n\x1a\nfixture")

    def make(value: str):
        captured["value"] = value
        return FakeImage()

    fake_qrcode.make = make
    monkeypatch.setitem(sys.modules, "qrcode", fake_qrcode)

    response = client.get(
        "/api/public/passports/PASS-DEMO-001/qr.png",
        params={"origin": "https://demo.skillpassport.test"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert captured["value"] == "https://demo.skillpassport.test/#/verify/PASS-DEMO-001"


def test_qr_route_fails_clearly_when_optional_module_is_unavailable(api, monkeypatch):
    client, _ = api
    real_import = builtins.__import__

    def without_qrcode(name, *args, **kwargs):
        if name == "qrcode":
            raise ImportError("simulated missing QR dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "qrcode", raising=False)
    monkeypatch.setattr(builtins, "__import__", without_qrcode)

    response = client.get("/api/public/passports/PASS-DEMO-001/qr.png")

    assert response.status_code == 503
    assert response.json()["detail"] == "QR support is unavailable"


@pytest.mark.parametrize(
    "path",
    [
        "/api/students/unknown/proofgraph",
        "/api/claims/unknown",
        "/api/challenges/unknown",
        "/api/opportunities/unknown",
        "/api/public/passports/unknown",
    ],
)
def test_unknown_resources_return_404(api, path):
    client, _ = api
    assert client.get(path).status_code == 404
