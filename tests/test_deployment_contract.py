import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_netlify_manifest_builds_generated_bundle_and_spa_fallback():
    manifest = tomllib.loads((ROOT / "netlify.toml").read_text(encoding="utf-8"))

    assert manifest["build"]["base"] == "frontend"
    assert manifest["build"]["publish"] == "dist"
    assert "build-netlify.test.mjs" in manifest["build"]["command"]
    assert "build-netlify.mjs" in manifest["build"]["command"]
    assert manifest["build"]["environment"]["NODE_VERSION"] == "20"

    fallback = next(
        item for item in manifest["redirects"] if item["from"] == "/*"
    )
    assert fallback == {"from": "/*", "to": "/index.html", "status": 200}

    runtime_headers = next(
        item for item in manifest["headers"] if item["for"] == "/runtime-config.js"
    )
    assert "no-store" in runtime_headers["values"]["Cache-Control"]


def test_frontend_loads_generated_public_config_before_application_code():
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    application = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    local_config = (ROOT / "frontend" / "runtime-config.js").read_text(
        encoding="utf-8"
    )
    build = (ROOT / "frontend" / "scripts" / "build-netlify.mjs").read_text(
        encoding="utf-8"
    )

    assert index.index('src="/runtime-config.js"') < index.index('src="/app.js"')
    assert "window.SKILLPASSPORT_CONFIG" in application
    assert 'normalizeRuntimeBase(runtimeConfig.apiBase, "/api")' in application
    assert "SKILLPASSPORT_API_BASE_URL" in build
    assert "VITE_API_BASE_URL" in build
    assert "PUBLIC_APP_BASE_URL" in build
    assert "DEPLOY_PRIME_URL" in build

    # The checked-in config is safe for same-origin local use; Netlify replaces it.
    assert 'apiBase: ""' in local_config
    assert 'publicAppBase: ""' in local_config
    for secret_name in ("MONGODB_URI", "GITHUB_TOKEN", "GEMINI_API_KEY"):
        assert secret_name not in local_config
    assert ".onrender.com" not in application


def test_render_blueprint_keeps_secrets_server_side_and_declares_cors_contract():
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "healthCheckPath: /api/health" in blueprint
    for secret_name in (
        "MONGODB_URI",
        "GITHUB_TOKEN",
        "GEMINI_API_KEY",
        "FRONTEND_URL",
        "PUBLIC_BASE_URL",
    ):
        assert re.search(
            rf"- key: {secret_name}\s+sync: false(?:\s|$)", blueprint
        )


def test_example_environment_and_docs_cover_split_hosting_contract():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    deployment = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")

    for name in (
        "FRONTEND_URL",
        "MONGODB_URI",
        "PUBLIC_BASE_URL",
        "SKILLPASSPORT_API_BASE_URL",
        "PUBLIC_APP_BASE_URL",
    ):
        assert re.search(rf"^{name}=", example, re.MULTILINE)

    assert "[Deployment](DEPLOYMENT.md)" in readme
    assert "ephemeral_render_fallback" in deployment
    assert "durable_mongodb" in deployment
    assert "frontend/dist" in deployment
