import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"

students = pd.read_csv(DATA / "students.csv")
courses = pd.read_csv(DATA / "student_courses.csv")
course_master = pd.read_csv(DATA / "courses.csv")
projects = pd.read_csv(DATA / "github_projects.csv")
languages = pd.read_csv(DATA / "github_languages.csv")
assessments = pd.read_csv(DATA / "assessment_results.csv")

# ---------------------------------------------------------
# COURSE EVIDENCE
# ---------------------------------------------------------

course_features = (
    courses
    .merge(course_master, on="course_id")
    .groupby(["student_id", "primary_skill"])
    .agg(
        course_count=("course_id", "count"),
        avg_marks=("marks", "mean")
    )
    .reset_index()
)

course_features.rename(
    columns={"primary_skill": "skill"},
    inplace=True
)

# ---------------------------------------------------------
# PROJECT EVIDENCE
# ---------------------------------------------------------

project_rows = []

for _, row in projects.iterrows():

    technologies = row["technologies"].split(", ")

    for skill in technologies:

        project_rows.append({
            "student_id": row["student_id"],
            "skill": skill,
            "project_count": 1,
            "project_stars": row["stars"],
            "project_complexity": (
                3 if row["complexity"] == "advanced"
                else 2 if row["complexity"] == "intermediate"
                else 1
            )
        })

project_features = pd.DataFrame(project_rows)

project_features = (
    project_features
    .groupby(["student_id", "skill"])
    .agg(
        project_count=("project_count", "sum"),
        project_stars=("project_stars", "sum"),
        avg_complexity=("project_complexity", "mean")
    )
    .reset_index()
)

# ---------------------------------------------------------
# ASSESSMENT EVIDENCE
# ---------------------------------------------------------

assessment_features = (
    assessments
    .groupby(["student_id", "skill"])
    .agg(
        assessment_count=("assessment_id", "count"),
        assessment_score=("final_score", "mean")
    )
    .reset_index()
)

# ---------------------------------------------------------
# COMBINE EVIDENCE
# ---------------------------------------------------------

all_skills = pd.DataFrame({
    "skill": course_master["primary_skill"].unique()
})

student_skill = (
    students[["student_id"]]
    .assign(key=1)
    .merge(all_skills.assign(key=1), on="key")
    .drop(columns="key")
)

training = student_skill.merge(
    course_features,
    on=["student_id", "skill"],
    how="left"
)

training = training.merge(
    project_features,
    on=["student_id", "skill"],
    how="left"
)

training = training.merge(
    assessment_features,
    on=["student_id", "skill"],
    how="left"
)

training = training.fillna(0)

# ---------------------------------------------------------
# TRAINING LABEL
# ---------------------------------------------------------
# Assessment score becomes our current ground truth.

training["verified_score"] = training["assessment_score"]

training["verified"] = (
    training["assessment_score"] >= 50
).astype(int)

training["proficiency"] = pd.cut(
    training["assessment_score"],
    bins=[-1, 49, 69, 84, 100],
    labels=[
        "Not Verified",
        "Beginner",
        "Intermediate",
        "Advanced"
    ]
)

# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

output = DATA / "training_dataset.csv"

training.to_csv(
    output,
    index=False
)

print("Training dataset created.")
print(f"Rows: {len(training)}")
print(f"Columns: {len(training.columns)}")
print(f"Saved: {output}")