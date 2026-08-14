"""Runtime configuration with no mandatory external services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(BASE_DIR / ".env")


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    store_path: Path
    fixture_path: Path
    mongodb_uri: str | None
    mongodb_database: str
    github_token: str | None
    gemini_api_key: str | None
    gemini_model: str
    challenge_timeout_seconds: float
    public_base_url: str | None
    cors_origins: tuple[str, ...] = ()
    port: int = 8000
    is_render: bool = False


def parse_frontend_urls(value: str | None) -> tuple[str, ...]:
    """Parse one or more comma/semicolon-separated browser origins."""
    if not value:
        return ()
    origins: list[str] = []
    for candidate in re.split(r"[,;]", value):
        candidate = candidate.strip().rstrip("/")
        if not candidate:
            continue
        parsed = urlparse(candidate)
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
            raise ValueError("FRONTEND_URL must contain only valid HTTP(S) origins")
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        if normalized not in origins:
            origins.append(normalized)
    return tuple(origins)


def parse_port(value: str | None) -> int:
    try:
        port = int(value or "8000")
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return port


def get_settings() -> Settings:
    store_value = os.getenv(
        "SKILLPASSPORT_STORE_PATH", str(DATA_DIR / "demo" / "runtime_store.json")
    )
    return Settings(
        store_path=Path(store_value).expanduser().resolve(),
        fixture_path=DATA_DIR / "demo" / "fixture.json",
        mongodb_uri=os.getenv("MONGODB_URI") or None,
        mongodb_database=os.getenv("MONGODB_DATABASE", "skillpassport"),
        github_token=os.getenv("GITHUB_TOKEN") or None,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        challenge_timeout_seconds=max(
            0.5, min(float(os.getenv("CHALLENGE_TIMEOUT_SECONDS", "3")), 10.0)
        ),
        public_base_url=os.getenv("PUBLIC_BASE_URL") or None,
        cors_origins=parse_frontend_urls(os.getenv("FRONTEND_URL")),
        port=parse_port(os.getenv("PORT")),
        is_render=bool(os.getenv("RENDER")),
    )
