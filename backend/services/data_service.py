from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def load_csv(path):
    return pd.read_csv(ROOT / path).fillna("").to_dict(orient="records")

def get_students():
    return load_csv("data/college/students.csv")

def get_student(student_id):
    rows = [x for x in get_students() if x["student_id"] == student_id]
    return rows[0] if rows else None

def get_skills():
    return load_csv("data/college/skills_master.csv")

def get_jobs():
    return load_csv("data/jobs/job_catalog.csv")

def get_assessment_attempts():
    return load_csv("data/assessments/assessment_attempts.csv")

def get_evidence():
    return load_csv("data/derived/evidence_records.csv")
