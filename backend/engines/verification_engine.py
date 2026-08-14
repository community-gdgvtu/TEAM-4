# Phase 1 verification logic.
# AI/adaptive assessment logic will be added later.

def proficiency(score: float) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Intermediate"
    if score >= 50:
        return "Beginner"
    return "Not Verified"

def verify_skill(score: float) -> dict:
    return {
        "score": round(score, 2),
        "proficiency": proficiency(score),
        "status": "Verified" if score >= 50 else "Needs Assessment"
    }
