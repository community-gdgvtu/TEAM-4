import joblib
import pandas as pd
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE
    / "backend"
    / "ml"
    / "models"
    / "skill_detection_model.joblib"
)


class SkillPredictor:

    def __init__(self):
        data = joblib.load(MODEL_PATH)

        self.model = data["model"]
        self.features = data["features"]

    def predict(
        self,
        course_count,
        avg_marks,
        project_count,
        project_stars,
        avg_complexity,
        assessment_count=0,
        assessment_score=0
    ):

        # Only use features used during model training
        input_data = pd.DataFrame([{
            "course_count": course_count,
            "avg_marks": avg_marks,
            "project_count": project_count,
            "project_stars": project_stars,
            "avg_complexity": avg_complexity
        }])

        # Ensure exact training feature order
        input_data = input_data[self.features]

        prediction = self.model.predict(input_data)[0]

        probability = self.model.predict_proba(
            input_data
        )[0][1]

        return {
            "skill_detected": bool(prediction),
            "confidence": round(
                float(probability) * 100,
                2
            )
        }


if __name__ == "__main__":

    predictor = SkillPredictor()

    result = predictor.predict(
        course_count=2,
        avg_marks=88,
        project_count=3,
        project_stars=25,
        avg_complexity=3
    )

    print("\nSkill Prediction")
    print("----------------")
    print(result)