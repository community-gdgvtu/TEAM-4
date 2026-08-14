"""One-process FastAPI application serving both API and frontend."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.core.config import FRONTEND_DIR, get_settings


settings = get_settings()

app = FastAPI(
    title="SkillPassport API",
    version="2.0.0",
    description="Inspectable evidence, deterministic proof challenges, and transparent opportunity coverage.",
)

app.add_middleware(
    CORSMiddleware,
    # Same-origin deployments need no CORS entry. FRONTEND_URL enables an
    # explicitly separate frontend without hardcoded development origins.
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router, prefix="/api")

# Frontend assets use /static/*. API routes are registered first and remain authoritative.
if FRONTEND_DIR.exists():
    index_template = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def serve_frontend(request: Request) -> HTMLResponse:
        """Serve metadata with an absolute social-card URL for the current host."""

        social_card_url = str(request.url_for("frontend-static", path="og.png"))
        return HTMLResponse(index_template.replace("__OG_IMAGE__", social_card_url))

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend-static")
    # Mount last so API routes always win. Hash routes remain client-side.
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
