# SkillPassport Demo Script

## The one-sentence pitch

> **A resume is a claim. SkillPassport shows the evidence — and lets you challenge it.**

The story is deliberately linear:

> **Claim → Doubt → Challenge → Proof → Opportunity**

Do not tour every screen. Let the FastAPI proof transition carry the demo.

## Before presenting

1. Run the automated checks from the repository root:

   ```bash
   pytest -q
   python -m compileall backend
   ```

2. Start the application:

   ```bash
   uvicorn backend.main:app --reload
   ```

3. Open `http://127.0.0.1:8000` in a clean browser tab.
4. Leave `GEMINI_API_KEY`, `GITHUB_TOKEN`, and `MONGODB_URI` unset for the most reliable offline path.
5. Reset the Judge Demo, then rehearse the exact known-good submission supplied by the active bundled challenge.
6. Confirm the initial FastAPI claim is `EVIDENCE_BACKED`, not already verified.
7. Confirm Opportunity Lens initially shows at least one verified/evidence-backed/missing distinction.
8. Confirm the public passport URL opens in a second tab. If demonstrating QR from another device, use a host that device can reach rather than `127.0.0.1`.
9. Close unrelated tabs, developer tools, notifications, and terminals containing environment variables.

## 90-second version

### 0:00–0:12 — Claim

**Click:** `View Judge Demo`

**Say:**

> “A resume tells you someone used FastAPI. SkillPassport shows why we believe that claim, what the evidence still cannot prove, and gives the candidate a relevant way to prove it.”

On the dashboard, briefly point to evidence artifacts, skill claims, evidence-backed skills, and challenge-verified skills. Do not explain every metric.

### 0:12–0:30 — Doubt

**Click:** `Analyze Evidence` → FastAPI `View Proof`

**Say:**

> “This is ProofGraph. We found the dependency, actual router implementation, API tests, candidate contribution signals, and supporting demo coursework. That is strong evidence—but we still do not call it verified.”

Point to the visible uncertainty, such as duplicate-resource error handling or request validation.

> “The interesting question is not just what we found. It is what we still do not know.”

### 0:30–0:58 — Challenge

**Click:** `Challenge this skill`

Complete the targeted concept check quickly, then place the rehearsed known-good response into the live task.

**Say:**

> “The challenge is grounded in this candidate’s evidence. Gemini can personalize the wording when configured, but it does not own the tests and cannot grant verified status.”

**Click:** the proof submission/run action.

As deterministic results appear, point to the individual checks and final passed count.

### 0:58–1:13 — Proof

Point to the state transition and VerificationEvent.

**Say:**

> “The server ran deterministic checks. Passing created a persistent VerificationEvent, promoted this claim to challenge-verified at the demonstrated level, and issued a tamper-evident Skill Stamp.”

Use this exact technical-judging sentence:

> **“We never allow an LLM response alone to create a verified skill. Gemini interprets and personalizes; inspectable evidence and deterministic execution control verification.”**

### 1:13–1:30 — Opportunity

**Click:** `Opportunity Lens` → bundled Tokyo backend opportunity.

**Say:**

> “The opportunity now distinguishes what is challenge-verified, merely evidence-backed, and still missing. Proof is not a separate assessment page—it immediately changes what this candidate can demonstrate for a real role.”

Finish on the updated FastAPI requirement or SkillPassport stamp.

## 3-minute version

### 0:00–0:15 — Landing page

**Show:** headline and product loop.

**Say:**

> “A resume is a claim. SkillPassport shows the evidence—and lets you challenge it. We start with technical students moving between India and Japan, where coursework and project work can be difficult to interpret across institutions.”

**Click:** `View Judge Demo`.

### 0:15–0:35 — Coherent candidate and evidence

On the dashboard, identify the fictional demo candidate, institution context, project snapshot, and demo academic evidence.

**Say:**

> “This is a deterministic fictional demo profile. The academic evidence is clearly labeled synthetic; we do not imply that Waseda or VTU systems are connected. Live GitHub analysis is available, but the snapshot keeps this demo independent of Wi-Fi and API limits.”

**Click:** `Analyze Evidence`.

### 0:35–0:58 — ProofGraph

**Click:** FastAPI `View Proof`, then open at least one source evidence node.

**Say:**

> “We do not infer FastAPI because a CSV says ‘FastAPI.’ The engine found inspectable signals: a dependency, router implementation, route behavior, tests, and candidate-attributed contribution metadata. Academic work corroborates the claim but cannot verify it.”

Point to the state label `EVIDENCE_BACKED`.

> “Evidence-backed means supported, not execution-verified. ProofGraph also identifies the remaining uncertainty.”

### 0:58–1:18 — Adaptive challenge rationale

Point to the evidence gap and target level.

**Say:**

> “Because the evidence is strong and tests are present, SkillPassport selects an intermediate challenge around the missing behavior—not a generic beginner quiz. The level and rationale are explainable.”

**Click:** `Challenge this skill`.

Answer the short targeted concept check.

> “This check is supporting context. It cannot verify the skill.”

### 1:18–1:47 — Live proof

Review the task in one sentence, then use the rehearsed known-good submission.

**Say:**

> “The candidate must preserve existing behavior while implementing the exact missing capability. The verifier owns the tests; candidate input cannot report its own pass status.”

**Click:** the proof submission/run action.

Let the result animation complete. Point to each deterministic check and the final passed count.

### 1:47–2:08 — VerificationEvent and stamp

Point to `CHALLENGE_VERIFIED`, demonstrated level, event ID, date, method, and integrity hash.

**Say:**

> “All required checks passed. The backend persisted a VerificationEvent, then derived this Skill Stamp. Refreshing the browser does not erase it because JavaScript state is not the source of truth.”

Use the core sentence:

> **“We never allow an LLM response alone to create a verified skill. Gemini interprets and personalizes; inspectable evidence and deterministic execution control verification.”**

If asked about the hash:

> “It is a tamper-evident integrity reference over the event—not a digital signature, identity proof, or global accreditation claim.”

### 2:08–2:38 — Opportunity Lens

**Click:** `Opportunity Lens` → bundled Tokyo backend opportunity.

Point to Python, FastAPI, SQL, and Docker requirement rows.

**Say:**

> “Opportunity Lens does not hide everything behind a 92 percent AI match. It shows which required capabilities are challenge-verified, which are evidence-backed, and which are missing.”

Point to the updated FastAPI requirement.

**Click:** `Prove this skill` on a supported evidence-backed or missing requirement, then immediately navigate back rather than completing a second challenge.

> “This closes the loop: an opportunity exposes a gap and routes directly to relevant proof.”

### 2:38–3:00 — Portable SkillPassport

**Click:** `SkillPassport` → FastAPI stamp → public verification/share action.

**Say:**

> “The final passport is a collection of inspectable Skill Stamps, not a decorative certificate. A recruiter can see the method, date, evidence summary, verification event, and public read-only record.”

End with:

> “SkillPassport does not ask employers to trust an AI score. It lets them inspect the claim, see the doubt, and verify the proof.”

## Contingencies

### Gemini is unavailable

Expected UI state: **Using deterministic challenge mode** or equivalent.

**Say:**

> “Gemini is an optional semantic layer. The application selected the known challenge template and opportunity taxonomy deterministically, so the verification path is unchanged.”

Continue the normal demo. Do not troubleshoot the API key on stage.

### GitHub is unavailable or rate-limited

Choose the bundled snapshot fallback.

**Say:**

> “The live integration uses bounded GitHub API calls, but judge-day reliability matters. This snapshot preserves real file paths, source signals, tests, and contribution metadata in the same evidence model.”

Continue from ProofGraph.

### MongoDB is unavailable

**Say:**

> “Persistence is behind an adapter. The demo uses the local file store by default; MongoDB is optional and does not change verification behavior.”

Continue without opening infrastructure settings.

### A challenge submission fails unexpectedly

1. Do not claim the skill verified.
2. Point out that failure correctly leaves the claim evidence-backed.
3. Use the visible retry/reset control or reset the Judge Demo.
4. If time is short, open the pre-issued public demo stamp only if it is explicitly labeled as part of the reset fixture; never pretend the failed attempt passed.

**Say:**

> “This is the trust boundary working: a runtime error cannot grant verified status.”

### Browser share or QR cannot open on a phone

Use the same-browser public verification link. Loopback URLs refer to the device displaying them and are not reachable from a separate phone.

### The audience asks to use a live repository

Do live ingestion only after the stable three-minute flow. Treat it as a bonus demonstration; never make it a prerequisite for the proof transition.

## Presenter guardrails

- Say **evidence-backed**, not “proven,” before the challenge passes.
- Say **challenge-verified at Intermediate level**, not “91% advanced.”
- Say **candidate contribution signal**, not “authorship verified.”
- Say **demo academic evidence**, not “connected university transcript.”
- Say **integrity hash**, not “blockchain credential” or “digital signature.”
- Say **constrained MVP runner**, not “cheat-proof production sandbox.”
- Do not describe Gemini as the verifier.
