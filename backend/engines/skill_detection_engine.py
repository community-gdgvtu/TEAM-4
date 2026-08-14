# Phase 1: deterministic skill detection.
# Phase 2: Gemini-assisted evidence interpretation will be added here.

def detect_skills(evidence_records):
    skill_scores = {}
    for record in evidence_records:
        skill_id = record["skill_id"]
        skill_scores.setdefault(skill_id, 0)
        skill_scores[skill_id] += 1
    return skill_scores
