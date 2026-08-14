# SkillPassport Engineering Guide

This file applies to the entire repository. Preserve these product and trust invariants in future changes.

## Product purpose

SkillPassport turns real evidence into an inspectable representation of demonstrated capability. The initial product wedge is Japan–India student and early-career technical talent.

The core loop is:

```text
Evidence → ProofGraph → Skill claim → Evidence gap → Proof Challenge
         → VerificationEvent → Skill Stamp → Opportunity Lens
```

The demo narrative is **Claim → Doubt → Challenge → Proof → Opportunity**. Features that do not strengthen this loop should not displace work on its reliability.

## Non-negotiable trust rules

1. **AI proposes. Engines prove.** An LLM may interpret or personalize, but it must never grant verified status or determine hidden test results.
2. Only deterministic proof verification may promote a claim to `CHALLENGE_VERIFIED`.
3. A passed challenge must create a persistent backend `VerificationEvent`. Browser state is never authoritative.
4. Keep `DETECTED`, `EVIDENCE_BACKED`, and `CHALLENGE_VERIFIED` distinct in models, APIs, copy, and UI.
5. Do not display opaque confidence or proficiency percentages as scientific verification.
6. Academic evidence supports a claim but cannot independently challenge-verify it. Bundled academic evidence must say **Demo academic evidence**.
7. Repository technology metadata alone is not proof. Prefer inspectable file, dependency, implementation, test, and contribution signals.
8. Do not reintroduce the legacy RandomForest or any opaque classifier into the live trust path.
9. Every optional integration must have a deterministic fallback. The full Judge Demo must work without network access, Gemini, GitHub credentials, or MongoDB.
10. Do not claim identity verification, cheat-proof execution, accreditation, employer certification, or production-grade sandboxing unless those properties are actually implemented and tested.

## Product behavior

- Start intentionally at the landing page; never auto-login a demo user.
- Keep **View Judge Demo** obvious and deterministic.
- Make evidence provenance inspectable from every skill claim.
- Show the remaining uncertainty before offering a Proof Challenge.
- Offer **Live proof available** only for a skill with a working deterministic verifier.
- A failed challenge or concept check alone must never promote a claim.
- **Prove this skill** must connect Opportunity Lens back to the relevant challenge.
- Passport stamps must be derived from persisted verification events.
- Public verification must be read-only and privacy-conscious.
- Every visible primary action must work. Do not ship placeholder or “coming soon” buttons.
- Use concise, accurate product copy and labels in addition to color for every trust state.

## Architecture boundaries

Keep these responsibilities separate even if the MVP implements them in a small number of modules:

- `EvidenceValidationEngine`: objective evidence and provenance
- `SkillClaimEngine`: claims, strength labels, state, relationships, and uncertainty
- `ProofVerificationEngine`: deterministic test results and VerificationEvents
- `OpportunityMatchingEngine`: transparent comparison of requirements with claim states
- GitHub service: bounded ingestion, validation, attribution metadata, and offline fallback
- Gemini service: optional structured proposals with schema validation and deterministic fallback
- Persistence adapter: equivalent file-store and optional MongoDB behavior

Do not accept client-provided pass status, test totals, verified level, or event hashes as authoritative. Derive them on the server from the selected challenge and deterministic results.

## Safety requirements

- Never execute candidate-provided shell commands.
- Constrain challenge input, isolate it in a temporary directory, remove secrets from the environment, disable network access where practical, and enforce strict time and output limits.
- Treat the MVP runner as an untrusted-code boundary and document its limitations.
- Validate GitHub hosts and construct bounded API requests to avoid SSRF and unbounded downloads.
- Escape or safely render all repository, evidence, opportunity, and public-profile text.
- Never log credentials, candidate source submissions, password material, or MongoDB connection strings.
- Hash passwords with a password-hashing algorithm; never store plaintext or unsalted fast hashes.
- Write file-backed persistence atomically and use temporary stores in tests.
- A SHA-256 verification hash is an integrity reference, not a signature or credential authority.

See `docs/SECURITY.md` for the complete security contract.

## Data and demo fixtures

- Keep the primary demo small, coherent, deterministic, and explicitly fictional.
- Keep profile, institution, coursework, repository snapshot, contribution metadata, claims, challenges, and opportunities mutually consistent.
- Preserve Japan and India relevance without implying real institution integrations.
- Do not use random Faker prose or large synthetic datasets as judge-facing proof.
- A demo reset must restore the same known state and may not depend on live services.

## Working practices

- Inspect the current branch and dirty working tree before editing. Preserve teammate changes and avoid unrelated rewrites.
- Keep FastAPI as the one-process application serving both the static frontend and API.
- Prefer relative API URLs in frontend code.
- Keep dependency declarations aligned with actual runtime imports; remove obsolete Firebase/ML dependencies when unused.
- Keep the implementation understandable enough to defend live. Fewer deeply integrated features are preferable to broad scaffolding.
- Update README and architecture documentation whenever trust behavior, state transitions, persistence, fallbacks, or run commands change.

## Required verification

Run from the repository root:

```bash
pytest -q
python -m compileall backend
```

When standalone JavaScript files exist, run `node --check` on each entry file. Then start the application with the documented Uvicorn command and manually smoke-test:

```text
Landing → Judge Demo → Analyze Evidence → View Proof → Challenge
        → Pass deterministic tests → Opportunity Lens → Passport
        → Public verification
```

Test with optional credentials unset. Also verify that a failed challenge cannot promote a claim and that a passed event survives store re-instantiation.
