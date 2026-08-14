from fastapi import APIRouter, HTTPException

from backend.ml.skill_intelligence import SkillIntelligence

router = APIRouter()

engine = SkillIntelligence()


@router.get("/student/{student_id}/skills")
def get_student_skills(student_id: str):

    try:
        results = engine.analyze(student_id)

        return {
            "student_id": student_id,
            "skills": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )