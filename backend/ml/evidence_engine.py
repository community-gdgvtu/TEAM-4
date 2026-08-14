import pandas as pd
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"


class EvidenceEngine:

    def __init__(self):

        self.courses = pd.read_csv(
            DATA / "student_courses.csv"
        )

        self.course_master = pd.read_csv(
            DATA / "courses.csv"
        )

        self.projects = pd.read_csv(
            DATA / "github_projects.csv"
        )

    def analyze_student(self, student_id):

        student_courses = self.courses[
            self.courses["student_id"] == student_id
        ]

        student_projects = self.projects[
            self.projects["student_id"] == student_id
        ]

        evidence = {}

        # -----------------------------
        # Academic Evidence
        # -----------------------------

        for _, course in student_courses.iterrows():

            course_info = self.course_master[
                self.course_master["course_id"]
                == course["course_id"]
            ]

            if course_info.empty:
                continue

            skill = course_info.iloc[0]["primary_skill"]

            if skill not in evidence:
                evidence[skill] = {
                    "courses": [],
                    "projects": []
                }

            evidence[skill]["courses"].append({
                "course": course_info.iloc[0]["course_name"],
                "marks": float(course["marks"]),
                "grade": course["grade"]
            })

        # -----------------------------
        # GitHub Evidence
        # -----------------------------

        for _, project in student_projects.iterrows():

            technologies = project[
                "technologies"
            ].split(", ")

            for skill in technologies:

                if skill not in evidence:
                    evidence[skill] = {
                        "courses": [],
                        "projects": []
                    }

                evidence[skill]["projects"].append({
                    "project": project["project_name"],
                    "stars": int(project["stars"]),
                    "complexity": project["complexity"],
                    "description": project["description"]
                })

        return evidence


if __name__ == "__main__":

    engine = EvidenceEngine()

    result = engine.analyze_student("STU0001")

    for skill, data in result.items():

        print("\n==============================")
        print(skill)
        print("==============================")

        print("Courses:")
        for course in data["courses"]:
            print(course)

        print("Projects:")
        for project in data["projects"]:
            print(project)