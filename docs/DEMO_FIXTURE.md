# Demo Fixture Contract

## Purpose

The bundled fixture guarantees a coherent, repeatable Judge Demo without GitHub, Gemini, MongoDB, or university-system access. It is product evidence for the architecture—not a claim about a real person or live institution integration.

The fixture must use the same normalized models and engine path as live evidence wherever practical. Avoid a separate frontend-only shortcut that bypasses validation, claim generation, challenge verification, or persistence.

## Required disclosure

Every fixture profile is fictional. Every bundled transcript or course record must visibly say:

> **Demo academic evidence**

Do not imply that Waseda University, Visvesvaraya Technological University, an employer, or GitHub has endorsed the candidate or connected a production data source.

## Narrative

The primary fixture represents a fictional India-based technical student applying to a Japan-based backend internship. An optional second fictional Japan-based student may demonstrate the reciprocal corridor, but must not complicate the main three-minute flow.

The primary story is:

```text
Coherent coursework + repository snapshot
  → Python / FastAPI / SQL claims
  → FastAPI is evidence-backed with one clear uncertainty
  → intermediate FastAPI Proof Challenge
  → deterministic pass creates VerificationEvent
  → Tokyo backend opportunity coverage changes
  → public Skill Stamp can be inspected
```

## Fixture components

### Candidate profile

Use a clearly fictional display name and a single stable student identifier. The institution, country, study area, email domain, GitHub username, and repository metadata must agree across every record and screen.

Required context:

- India-based technical student
- fictional/demo association with a VTU-context institution
- computer science, software engineering, or adjacent study area
- explicit application interest in Japan
- no real-person portrait or personal data

### Academic evidence

Include a small intentional record such as:

- API or web-service development coursework supporting Python/FastAPI concepts;
- database coursework supporting SQL fundamentals; and
- grades or completion indicators used only as corroboration.

Academic data may help an evidence-backed claim but must never create `CHALLENGE_VERIFIED`.

### Repository snapshot

The offline snapshot should contain normalized metadata for a small backend project with inspectable evidence such as:

```text
requirements.txt
backend/main.py
backend/api/routes.py
backend/models.py
tests/test_api.py
schema.sql or repository/database code
```

The exact paths may follow the implemented fixture, but the visible evidence should include:

- Python source substantial enough to inspect;
- a FastAPI dependency;
- `FastAPI(...)` or `APIRouter` usage;
- route decorators and request/response validation;
- API tests;
- SQL schema/query or ORM usage;
- a bounded set of recent commits; and
- candidate-attribution metadata labeled as a contribution signal.

Do not grant a claim solely because snapshot metadata lists a technology name.

### Initial skill states

The reset state should demonstrate meaningful distinctions:

| Skill | Expected initial state | Reason |
|---|---|---|
| Python | Evidence-backed or challenge-verified only if backed by an explicit fixture event | Substantive source and tests |
| FastAPI | `EVIDENCE_BACKED` | Dependency, implementation, tests, and contribution signal |
| SQL | `EVIDENCE_BACKED` or `DETECTED` | Database source plus supporting coursework |
| Docker | Missing/unproven | Creates a clear opportunity gap |

FastAPI must not begin challenge-verified in the primary live-proof story.

### FastAPI evidence gap and challenge

Use one concise uncertainty that the repository evidence cannot answer directly, such as duplicate-resource conflict handling or request-validation behavior.

The challenge should:

- be labeled Intermediate when justified by the evidence;
- explain why that level was selected;
- include no more than three targeted concept questions;
- require a narrowly constrained implementation or patch;
- preserve existing behavior;
- have clear public examples and server-owned deterministic tests;
- show individual checks and a final passed count; and
- create a VerificationEvent only when every required check passes.

Keep a rehearsable known-good submission available to the demo team without pre-populating the candidate editor in a way that makes the proof look automatic.

### Opportunities

Include at least:

1. a Japan-based backend internship with Python, FastAPI, SQL, and a preferred or missing capability such as Docker or Japanese proficiency; and
2. an India-based technical opportunity using overlapping but non-identical requirements.

The Tokyo opportunity should visibly change after FastAPI verification. Required and preferred requirements must remain distinguishable.

Include Japanese or mixed-language source text in at least one bundled opportunity so the semantic/fallback story is demonstrable without building a general translation product.

## Reset behavior

The Judge Demo reset should be idempotent:

1. remove prior demo attempts/events from the active demo store;
2. restore the exact fictional profile, evidence, claims, challenges, and opportunities;
3. restore FastAPI to `EVIDENCE_BACKED`;
4. preserve no state in browser-only storage that contradicts the backend; and
5. produce the same stable identifiers where the implementation relies on them.

Reset must be limited to demo data. It should be disabled or access-controlled outside a demo environment before public deployment.

## Determinism and provenance checks

- The fixture loads with optional credentials unset and no network.
- Repeated reset produces the same pre-challenge claim states.
- Every evidence node has a nonempty source reference.
- Academic nodes carry the demo label.
- The failed FastAPI submission leaves the claim evidence-backed.
- The known-good submission produces the expected deterministic result.
- The event survives store re-instantiation.
- Passport and Opportunity Lens derive their updated state from that persisted event.
- Public verification exposes only intended fields.
- Fixture text contains no real credentials, private repository content, or accidental real-person data.

## Maintenance

When taxonomy rules, challenge templates, API models, or persistence schemas change, update the fixture and its tests together. Large randomized CSV datasets may remain as development artifacts only if clearly separated; they must not silently replace the intentional Judge Demo records.
