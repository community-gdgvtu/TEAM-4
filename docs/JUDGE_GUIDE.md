# SkillPassport Judge Guide

## What judges should remember

SkillPassport is not an AI resume writer. It is a challengeable trust layer for capability claims:

```text
Claim → Doubt → Challenge → Proof → Opportunity
```

The key product idea is simple:

> **A resume is a claim. SkillPassport shows the evidence — and lets you challenge it.**

The key engineering rule is equally simple:

> **AI proposes. Engines prove.**

## Rubric map

### Technical Implementation — 30%

| Capability | What to show | Why it matters |
|---|---|---|
| Bounded GitHub ingestion | Repository URL input, provenance-rich file/test/commit evidence, and failure fallback | This is evidence extraction, not a hardcoded technology badge. |
| Offline repository snapshot | Same normalized evidence model without network access | The full architecture remains demonstrable under judge-day constraints. |
| Deterministic evidence validation | Dependency, source, tests, contribution, and academic signals with explicit rules | Evidence is inspectable and repeatable. |
| ProofGraph | Open a FastAPI claim and inspect source-linked nodes and uncertainty | Judges can answer “why does the system believe this?” |
| Trust lifecycle | `DETECTED` → `EVIDENCE_BACKED` → `CHALLENGE_VERIFIED` | Detection is not mislabeled as verification. |
| Deterministic challenge runner | Submit the FastAPI proof task and show individual test results | Verification depends on execution, not an LLM score. |
| Persistent VerificationEvent | Refresh/reopen the claim and show event ID, method, date, result, and hash | Backend persistence is the source of truth. |
| Optional Gemini structured output | Explain schema validation and fallback | Semantic intelligence is bounded by deterministic authority. |
| Persistence abstraction | Default file store and optional MongoDB adapter | The demo is reliable while the deployment path remains extensible. |
| Public verification | Open a shared read-only stamp/passport route | Proof is portable and inspectable outside the candidate dashboard. |

Technical sentence to use verbatim:

> **“We never allow an LLM response alone to create a verified skill. Gemini interprets and personalizes; inspectable evidence and deterministic execution control verification.”**

### Innovation & Originality — 20%

1. **Challengeable skill claims:** The system does not stop at detection or evidence aggregation; it asks what the evidence still cannot prove.
2. **Repo-grounded proof:** The challenge is selected from a real evidence gap instead of an unrelated generic assessment.
3. **Inspectable ProofGraph:** Each claim exposes evidence, provenance, corroboration, and uncertainty.
4. **Trust lifecycle:** The product visibly distinguishes detection, evidence, and execution-verified proof.
5. **Closed opportunity loop:** A requirement gap links directly to proof, and passing changes opportunity coverage.

The strongest comparison is not “we use more AI.” It is:

> “Most career products summarize claims. SkillPassport makes the claim inspectable and challengeable.”

### Business Potential — 20%

#### Initial wedge

Students and early-career engineers moving between India and Japan often present coursework and project experience that recruiters must interpret across different institutional and hiring contexts. SkillPassport provides a common evidence and proof vocabulary without pretending the institutions are already integrated.

#### Users and value

| User | Immediate value |
|---|---|
| Student/candidate | Turns overlooked coursework and project work into inspectable, challenge-verifiable capability. |
| Recruiter | Separates claims, supporting evidence, and execution-verified proof before an interview. |
| University/career office | Helps students communicate capability across borders while retaining evidence provenance. |
| Employer | Can author role-specific challenges and interpret proof against explicit requirements. |

#### Expansion path

- University- and employer-issued evidence connectors
- Employer-authored challenge libraries
- Stronger identity and issuer signatures
- Standards-based credential export
- Freshness and re-verification policies
- Additional country and profession corridors

The defensible asset is not a generic job catalogue. It is the structured relationship among evidence, uncertainty, deterministic proof, and opportunity requirements.

### UI/UX — 15%

Show these interactions rather than enumerating screens:

1. Landing page communicates the thesis immediately.
2. Judge Demo removes setup friction.
3. Dashboard emphasizes evidence and trust progression.
4. ProofGraph uses labels and visual hierarchy to distinguish states.
5. Evidence nodes reveal provenance on demand rather than overwhelming the user.
6. Proof Lab explains why the challenge was chosen and makes the test transition satisfying.
7. Opportunity Lens uses a readable requirement matrix rather than an opaque percentage.
8. Skill Stamps expose method, date, event ID, evidence summary, freshness, and integrity reference.
9. Public verification and share/print actions work.
10. Loading, empty, error, keyboard, responsive, and offline states are deliberate.

The main visual moment is the claim transitioning from `EVIDENCE_BACKED` to `CHALLENGE_VERIFIED` after deterministic tests pass.

### Presentation & Communication — 15%

Use the three-minute sequence:

```text
Landing thesis
  → coherent fictional candidate
  → inspect FastAPI ProofGraph
  → reveal one evidence gap
  → run one grounded challenge
  → show persistent VerificationEvent
  → show changed opportunity coverage
  → end on public Skill Stamp
```

Keep technical explanations concrete:

- “This dependency detected the skill.”
- “These implementation and test signals made it evidence-backed.”
- “This uncertainty selected the challenge.”
- “These server-owned tests created the VerificationEvent.”
- “That event changed this requirement from evidence-backed to challenge-verified.”

Avoid a feature tour and avoid spending demo time on signup, settings, or optional integrations.

## Likely judge questions

### “Is this just keyword matching?”

No. A keyword or dependency can create a detected signal, but stronger claims require inspectable implementation, tests, contribution, and corroborating evidence. Only a relevant deterministic challenge can create `CHALLENGE_VERIFIED`.

### “What if Gemini hallucinates?”

Gemini output is a schema-validated proposal. Supported templates, deterministic evidence rules, hidden tests, and claim transitions remain server-controlled. Invalid or unavailable AI output triggers a deterministic fallback.

### “Why not use the RandomForest confidence model?”

The earlier experiment learned labels derived from substantially the same evidence features, making impressive confidence values misleading. It is intentionally outside the trust path. Explainability and deterministic proof are stronger engineering choices here.

### “Does a GitHub repository prove the candidate wrote the code?”

No. File evidence shows what exists in the repository, and commit metadata can provide a candidate-attribution signal. SkillPassport does not claim identity or authorship verification. The challenge adds direct capability evidence without overstating provenance.

### “Can candidates cheat or escape the runner?”

The MVP constrains task shape, process behavior, time, output, environment, and network where practical. It is not represented as a production hostile-code sandbox. A production system would use stronger container or microVM isolation, resource quotas, monitoring, and separate worker infrastructure.

### “Is the hash a credential or blockchain?”

No. It is a SHA-256 integrity reference over canonical VerificationEvent data. It helps detect mutation; it is not a digital signature, identity proof, issuer accreditation, or blockchain claim.

### “Are Waseda and VTU connected?”

No. Bundled academic records are fictional and explicitly labeled **Demo academic evidence**. Institution integrations are a future consent-based expansion.

### “Why Japan and India?”

The hackathon provides a natural initial corridor with real cross-context interpretation challenges. Starting with a narrow technical-talent wedge creates a clearer user, demo, and go-to-market story than claiming a universal credential network on day one.

### “What happens without Wi-Fi or credentials?”

The repository snapshot, deterministic challenge templates, taxonomy-based opportunity extraction, and local file store support the complete demo. GitHub, Gemini, and MongoDB enhance the system but are not required.

### “What prevents the frontend from marking itself verified?”

The frontend cannot author a VerificationEvent. The server associates the challenge with its claim and candidate, runs owned deterministic checks, derives pass status and test counts, persists the event, and then promotes the claim.

## Honest claim vocabulary

| Prefer | Avoid |
|---|---|
| Evidence-backed | Proven expert |
| Challenge-verified at Intermediate level | 96.4% mastery |
| Candidate contribution signal | Authorship verified |
| Demo academic evidence | Connected university transcript |
| VerificationEvent integrity hash | Certified blockchain credential |
| Constrained MVP challenge runner | Cheat-proof sandbox |
| Public read-only verification | Globally accredited passport |

## Final readiness checklist

- Landing page opens first; no accidental demo login.
- Judge Demo completes without optional credentials.
- Evidence nodes show concrete source references.
- FastAPI starts evidence-backed and is promoted only after a passing challenge.
- A failed challenge cannot promote a claim.
- Verification survives a refresh/store re-instantiation.
- Opportunity coverage changes after verification.
- Public passport route, share action, QR, and print/export flow work.
- No visible primary action is a placeholder.
- No secret, token, private repository content, or plaintext password appears in UI or logs.
- Automated tests, compile check, and one-process smoke test pass.
