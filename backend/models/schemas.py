from pydantic import BaseModel

class VerifiedSkill(BaseModel):
    skill_id: str
    skill_name: str
    score: float
    proficiency: str
    status: str
