"""Academic evidence access. Bundled records are always explicitly labelled demo data."""

from __future__ import annotations

from typing import Any

from backend.core.taxonomy import normalize_skill


class AcademicService:
    def records_for_student(
        self, data: dict[str, Any], student: dict[str, Any]
    ) -> list[dict[str, Any]]:
        records = [
            dict(record)
            for record in data.get("academic_records", [])
            if record.get("student_id") == student["id"]
        ]
        for record in records:
            record["evidence_label"] = (
                "Demo academic evidence" if record.get("demo") else "Academic evidence"
            )

        if student.get("academic_source") == "manual":
            for index, course in enumerate(student.get("manual_coursework", []), start=1):
                skills = [normalize_skill(skill) or skill for skill in course.get("skills", [])]
                records.append(
                    {
                        "id": f"ACAD-MANUAL-{student['id']}-{index}",
                        "student_id": student["id"],
                        "course_name": course["course_name"],
                        "grade": course["grade"],
                        "skills": skills,
                        "institution": student["institution"],
                        "demo": False,
                        "evidence_label": "Candidate-entered academic evidence",
                    }
                )
        return records

