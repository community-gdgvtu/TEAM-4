# Deterministic MVP job matcher.
# Later this can use richer skill semantics and Gemini explanations.

LEVEL = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}

def match_jobs(verified_skills, jobs):
    results = []
    for job in jobs:
        required = [x.strip() for x in job["required_skills"].split(";")]
        matched = 0
        for req in required:
            item = next((s for s in verified_skills if s["skill_name"].lower() == req.lower()), None)
            if item and LEVEL.get(item["proficiency"], 0) >= LEVEL.get(job["minimum_proficiency"], 1):
                matched += 1
        score = round((matched / len(required)) * 100, 1) if required else 0
        results.append({**job, "compatibility": score})
    return sorted(results, key=lambda x: x["compatibility"], reverse=True)
