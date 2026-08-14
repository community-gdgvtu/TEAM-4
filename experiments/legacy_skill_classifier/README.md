# Legacy skill classifier experiment

This directory preserves the teammate's original RandomForest baseline and its
large random synthetic CSV dataset for historical reference only.

The experiment derives its training target from substantially the same course
and project-count features used for prediction. Its near-perfect probabilities
therefore do not constitute independent skill verification. Nothing under this
directory is imported by the production FastAPI application.

SkillPassport's production trust path is deterministic:

1. inspectable evidence creates a skill claim;
2. multiple direct/corroborating signals can make it evidence-backed;
3. only server-owned proof-challenge tests can create a VerificationEvent and
   promote a claim to `CHALLENGE_VERIFIED`.

The archived data is synthetic load/experiment material, not judge-demo proof.

