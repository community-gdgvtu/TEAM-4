# Deploy SkillPassport on Render and Netlify

This is the supported split deployment:

```text
Netlify (static frontend) -- HTTPS / CORS --> Render (FastAPI /api)
                                                |
                                                +-- MongoDB (durable, recommended)
                                                +-- JSON file (demo fallback, ephemeral on Render)
```

The frontend contains only public URLs. Keep `MONGODB_URI`, `GITHUB_TOKEN`, and
`GEMINI_API_KEY` on Render.

## 1. Deploy the Render API

1. Push the repository to a Git provider supported by Render.
2. In Render, choose **New > Blueprint**, connect the repository, and select the
   branch to deploy. Render reads the root `render.yaml`.
3. Supply the Blueprint's secret values when prompted:
   - `MONGODB_URI`: recommended for durable verification history; it may be left
     empty only for a disposable demo.
   - `GITHUB_TOKEN`: optional live GitHub access.
   - `GEMINI_API_KEY`: optional structured interpretation. Verification remains
     deterministic without it.
   - Leave `FRONTEND_URL` and `PUBLIC_BASE_URL` empty until the Netlify origin is
     known.
4. Create the service. Do not override the build, start, or health-check commands
   declared in `render.yaml`:

   ```text
   Runtime: Python
   Build:   pip install -r backend/requirements.txt
   Start:   python -m backend.start
   Health:  /api/health
   ```

   Do not set `PORT`; Render supplies it and `backend.start` binds it on
   `0.0.0.0`.
5. Record the service origin, for example
   `https://skillpassport-api.onrender.com`, and open:

   ```text
   https://skillpassport-api.onrender.com/api/health
   ```

The response should report `"status":"ok"`. For a durable deployment,
`persistence_durability` must be `durable_mongodb`.

## 2. Deploy the Netlify frontend

1. In Netlify, choose **Add new project > Import an existing project** and select
   the same repository and branch.
2. Keep the settings from the root `netlify.toml`. It sets `frontend` as the base,
   runs the checked build script with Node 20, and publishes `frontend/dist`.
3. Add this Netlify build environment variable:

   | Variable | Value | Required? |
   |---|---|---|
   | `SKILLPASSPORT_API_BASE_URL` | Render origin plus `/api`, for example `https://skillpassport-api.onrender.com/api` | Yes for split hosting |
   | `PUBLIC_APP_BASE_URL` | Final Netlify/custom origin, for example `https://skillpassport.netlify.app` | Optional; Netlify's deployment URL is the fallback |

   `VITE_API_BASE_URL` is accepted only as a compatibility fallback. Prefer
   `SKILLPASSPORT_API_BASE_URL`.
4. Deploy and record the production origin, for example
   `https://skillpassport.netlify.app`.

Never add backend credentials to Netlify. The build generates
`dist/runtime-config.js`, which is public browser configuration.

## 3. Connect the two origins

Return to the Render service and set:

```dotenv
FRONTEND_URL=https://skillpassport.netlify.app
PUBLIC_BASE_URL=https://skillpassport.netlify.app
```

`FRONTEND_URL` is the CORS allowlist. It accepts comma- or semicolon-separated
HTTP(S) origins when both a Netlify origin and a custom domain are needed. Use
origins only: no path, query, credentials, or wildcard. Netlify deploy previews
have distinct origins; add a preview's exact origin only when it needs API access.

`PUBLIC_BASE_URL` fixes backend-generated QR targets to the user-facing frontend.
Save the variables and redeploy Render. If the API or app origin changes, update
the corresponding environment variables and redeploy the affected service; do not
edit the generated runtime config by hand.

## 4. Verify the deployment

- Render `/api/health` returns `status: ok`, the expected `cors_origins`, and the
  intended persistence durability.
- The Netlify landing page loads without missing JavaScript, CSS, or social-card
  assets.
- **View Judge Demo** can reset the fixture, analyze evidence, fail and pass a
  challenge, show updated opportunity coverage, and issue a passport.
- The public passport opens in a signed-out/private window and its QR points to the
  Netlify or custom origin.
- Browser developer tools show API calls to the configured Render `/api` prefix,
  with no credential values in the static files.

## Persistence warning

The Blueprint's JSON store at `/tmp/skillpassport/runtime_store.json` is an
availability fallback, not durable Render persistence. Render instances have an
ephemeral filesystem, so JSON state can be lost on a restart, redeploy, or instance
replacement. When `MONGODB_URI` is absent or MongoDB cannot be reached,
`/api/health` reports
`ephemeral_render_fallback`. Configure a reachable MongoDB deployment and confirm
`durable_mongodb` before relying on issued verification history.

The repository does not declare a Render persistent disk. Adding one is a separate
infrastructure choice and requires pointing `SKILLPASSPORT_STORE_PATH` at its mount
path.

## Troubleshooting

| Symptom | Check |
|---|---|
| Browser reports a network or CORS error | Confirm Render is healthy and `FRONTEND_URL` exactly matches `window.location.origin`; then redeploy Render. |
| API requests return 404 | `SKILLPASSPORT_API_BASE_URL` must be an absolute HTTPS URL ending in `/api`; update it and trigger a Netlify deploy. |
| Netlify build rejects a URL | Public URL settings must be absolute HTTP(S) URLs. Remove credentials, fragments, and non-HTTP schemes. |
| Landing page loads but assets are missing | Confirm Netlify used the root `netlify.toml` and published `frontend/dist`, not the source directory. |
| Data disappears after a Render restart | Check `persistence_durability`; set a valid `MONGODB_URI` and redeploy. |
| QR opens the Render host or an old site | Set `PUBLIC_BASE_URL` on Render and `PUBLIC_APP_BASE_URL` on Netlify to the final frontend origin, then redeploy both. |
| Gemini or live GitHub is unavailable | Leave the optional key unset or correct it. The bundled snapshot, deterministic templates, and rules remain usable. |

Platform references: [Render Blueprint specification](https://render.com/docs/blueprint-spec),
[Render filesystem and disks](https://render.com/docs/disks), and
[Netlify file-based configuration](https://docs.netlify.com/build/configure-builds/file-based-configuration/).
