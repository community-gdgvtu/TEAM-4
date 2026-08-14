# SkillPassport — Deploy Now

## 1) Render backend

Create a Render **Blueprint** from this repository (the root `render.yaml` is ready), or create a Python Web Service with:

- Build: `pip install -r backend/requirements.txt`
- Start: `python -m backend.start`
- Health check: `/api/health`

Set these Render environment variables:

- `FRONTEND_URL` — leave empty until Netlify has a final URL, then set it to that exact origin, e.g. `https://your-site.netlify.app`
- `PUBLIC_BASE_URL` — set to the same final Netlify origin
- `MONGODB_URI` — recommended for durable verification records; without it the demo uses Render's ephemeral JSON fallback
- `GITHUB_TOKEN` — optional; enables more reliable live GitHub evidence ingestion
- `GEMINI_API_KEY` — optional; enables Gemini personalization/requirement parsing
- `GEMINI_MODEL` — defaults to `gemini-2.5-flash`

Confirm: `https://YOUR-RENDER-SERVICE.onrender.com/api/health`

## 2) Netlify frontend

Import the same repository into Netlify. `netlify.toml` is ready.

Set the Netlify build environment variable:

- `SKILLPASSPORT_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api`

Optional:

- `PUBLIC_APP_BASE_URL=https://YOUR-SITE.netlify.app`

Deploy. The build creates `frontend/dist` automatically.

## 3) Connect the two origins

After Netlify gives the final URL, return to Render and set:

- `FRONTEND_URL=https://YOUR-SITE.netlify.app`
- `PUBLIC_BASE_URL=https://YOUR-SITE.netlify.app`

Redeploy Render.

## 4) Judge-demo smoke test

Open Netlify and click **View Judge Demo**, then verify this path:

1. Dashboard
2. Analyze Evidence
3. ProofGraph → FastAPI → Challenge Skill
4. Load judge-demo response → Run deterministic verification → **5/5 PASS**
5. Opportunity Lens → Tokyo Backend Engineering Internship → FastAPI now challenge-verified; SQL remains evidence-backed
6. SkillPassport → public verification / QR

If GitHub, Gemini, or MongoDB is unavailable, the judge demo still works using deterministic bundled fallbacks.
