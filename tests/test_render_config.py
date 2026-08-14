from types import SimpleNamespace
from pathlib import Path

import pytest

from backend.core.config import get_settings, parse_frontend_urls, parse_port


def test_frontend_url_supports_multiple_normalized_origins():
    assert parse_frontend_urls(
        "https://skillpassport.netlify.app/, https://preview.example.com"
    ) == (
        "https://skillpassport.netlify.app",
        "https://preview.example.com",
    )


@pytest.mark.parametrize(
    "value",
    ["*", "https://user@example.com", "https://example.com/path", "javascript:alert(1)"],
)
def test_frontend_url_rejects_non_origin_values(value):
    with pytest.raises(ValueError):
        parse_frontend_urls(value)


def test_render_settings_read_port_cors_and_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("FRONTEND_URL", "https://skillpassport.netlify.app")
    monkeypatch.setenv("SKILLPASSPORT_STORE_PATH", str(tmp_path / "runtime.json"))
    settings = get_settings()
    assert settings.port == 10000
    assert settings.is_render is True
    assert settings.cors_origins == ("https://skillpassport.netlify.app",)


@pytest.mark.parametrize("value", ["0", "65536", "abc"])
def test_port_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_port(value)


def test_start_entrypoint_binds_all_interfaces_and_configured_port(monkeypatch):
    import backend.start as start

    captured = {}
    monkeypatch.setattr(start, "get_settings", lambda: SimpleNamespace(port=12345))
    monkeypatch.setattr(start.uvicorn, "run", lambda *args, **kwargs: captured.update({"args": args, **kwargs}))
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.1")
    start.main()
    assert captured["args"] == ("backend.main:app",)
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 12345
    assert captured["forwarded_allow_ips"] == "10.0.0.1"


def test_render_blueprint_declares_native_build_start_and_health_contract():
    blueprint = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(
        encoding="utf-8"
    )
    assert "runtime: python" in blueprint
    assert "buildCommand: pip install -r backend/requirements.txt" in blueprint
    assert "startCommand: python -m backend.start" in blueprint
    assert "healthCheckPath: /api/health" in blueprint
    assert "value: /tmp/skillpassport/runtime_store.json" in blueprint
