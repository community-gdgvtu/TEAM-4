# SkillPassport Architecture — Phase 1

```text
HTML/CSS/JS
    |
    v
FastAPI REST API
    |
    +--> Data Service
    |
    +--> Skill Detection Engine
    |
    +--> Verification Engine
    |
    +--> Job Matching Engine
    |
    v
Synthetic CSV datasets

Future:
Firebase/Firestore
Gemini intelligence layer
GitHub integration
Institution integration
Adaptive proctored assessments
```

The current version deliberately avoids AI. This gives us a deterministic baseline against which the later AI layer can be evaluated.
