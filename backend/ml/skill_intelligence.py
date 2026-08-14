import pandas as pd
from pathlib import Path

from backend.ml.evidence_engine import EvidenceEngine
from backend.ml.predict_skill import SkillPredictor


BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"


class SkillIntelligence:

    def __init__(self):
        self.evidence_engine = EvidenceEngine()
        self.predictor = SkillPredictor()

    def analyze(self, student_id):

        evidence = self.evidence_engine.analyze_student(
            student_id
        )

        results = []

        for skill, data in evidence.items():

            courses = data["courses"]
            projects = data["projects"]

            # Academic features
            course_count = len(courses)

            avg_marks = (
                sum(c["marks"] for c in courses)
                / course_count
                if course_count
                else 0
            )

            # Project features
            project_count = len(projects)

            project_stars = sum(
                p["stars"] for p in projects
            )

            complexity_map = {
                "beginner": 1,
                "intermediate": 2,
                "advanced": 3
            }

            avg_complexity = (
                sum(
                    complexity_map.get(
                        p["complexity"],
                        1
                    )
                    for p in projects
                )
                / project_count
                if project_count
                else 0
            )

            # ML prediction
            prediction = self.predictor.predict(
                course_count=course_count,
                avg_marks=avg_marks,
                project_count=project_count,
                project_stars=project_stars,
                avg_complexity=avg_complexity
            )

            results.append({
                "skill": skill,
                "confidence": prediction["confidence"],
                "skill_detected": prediction["skill_detected"],
                "assessment_required": prediction["skill_detected"],
                "evidence": {
                    "courses": courses,
                    "projects": projects
                }
            })

        return results


if __name__ == "__main__":

    engine = SkillIntelligence()

    results = engine.analyze("STU0001")

    print("\n================================")
    print("SKILL INTELLIGENCE")
    print("================================")

    for result in results:

        print(
            f"\n{result['skill']}"
        )

        print(
            f"Confidence: "
            f"{result['confidence']}%"
        )

        print(
            f"Assessment: "
            f"{'YES' if result['assessment_required'] else 'NO'}"
        )