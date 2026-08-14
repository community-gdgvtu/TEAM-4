"""Create inspectable evidence items from bounded repository and academic sources."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from backend.core.taxonomy import SKILLS, normalize_skill
from backend.models.schemas import (
    EvidenceDirectness,
    EvidenceItem,
    EvidenceSourceType,
)


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


class EvidenceValidationEngine:
    SOURCE_TYPE = {
        "code": EvidenceSourceType.GITHUB_CODE,
        "dependency": EvidenceSourceType.GITHUB_DEPENDENCY,
        "test": EvidenceSourceType.GITHUB_TEST,
    }

    def analyze(
        self,
        student: dict[str, Any],
        snapshot: dict[str, Any],
        academic_records: list[dict[str, Any]],
    ) -> list[EvidenceItem]:
        now = datetime.now(timezone.utc)
        output: list[EvidenceItem] = []
        seen: set[str] = set()
        path_skills: dict[str, set[str]] = {}

        for file_info in snapshot.get("files", []):
            path = str(file_info.get("path", ""))
            content = str(file_info.get("content", ""))[:100_000]
            for skill, definition in SKILLS.items():
                for rule in definition.rules:
                    if not rule.path_matches(path) or not rule.content_matches(content):
                        continue
                    key = f"{skill}|{rule.id}|{path}"
                    if key in seen:
                        continue
                    seen.add(key)
                    path_skills.setdefault(path, set()).add(skill)
                    output.append(
                        EvidenceItem(
                            id=stable_id("EVD", student["id"], key),
                            student_id=student["id"],
                            source_type=self.SOURCE_TYPE[rule.source_kind],
                            skill=skill,
                            title=rule.title,
                            source_ref=path,
                            directness=EvidenceDirectness(rule.directness),
                            summary=rule.summary,
                            metadata={
                                "repository": snapshot.get("repository_url"),
                                "branch": snapshot.get("branch", "main"),
                                "signal_rule": rule.id,
                                "demo_snapshot": bool(snapshot.get("is_demo_snapshot")),
                            },
                            created_at=now,
                        )
                    )

        username = (student.get("github_username") or "").lower()
        for commit in snapshot.get("commits", []):
            if username and (commit.get("author_login") or "").lower() != username:
                continue
            skills = {
                skill
                for path in commit.get("paths", [])
                for skill in path_skills.get(path, set())
            }
            skills.add("Git")
            for skill in skills:
                key = f"{skill}|commit|{commit.get('sha')}"
                if key in seen:
                    continue
                seen.add(key)
                output.append(
                    EvidenceItem(
                        id=stable_id("EVD", student["id"], key),
                        student_id=student["id"],
                        source_type=EvidenceSourceType.GITHUB_COMMIT,
                        skill=skill,
                        title="Candidate contribution signal",
                        source_ref=f"commit:{commit.get('sha', 'unknown')}",
                        directness=(
                            EvidenceDirectness.DIRECT
                            if skill == "Git"
                            else EvidenceDirectness.CORROBORATING
                        ),
                        summary="A recent commit attributed to the configured GitHub username touches relevant files.",
                        metadata={
                            "message": commit.get("message", ""),
                            "date": commit.get("date"),
                            "paths": commit.get("paths", []),
                            "attribution": "username_match_signal_not_identity_verification",
                            "demo_snapshot": bool(snapshot.get("is_demo_snapshot")),
                        },
                        created_at=now,
                    )
                )

        for record in academic_records:
            for raw_skill in record.get("skills", []):
                skill = normalize_skill(str(raw_skill)) or str(raw_skill)
                if skill not in SKILLS:
                    continue
                key = f"{skill}|academic|{record.get('id')}"
                if key in seen:
                    continue
                seen.add(key)
                label = record.get("evidence_label", "Academic evidence")
                output.append(
                    EvidenceItem(
                        id=stable_id("EVD", student["id"], key),
                        student_id=student["id"],
                        source_type=EvidenceSourceType.ACADEMIC,
                        skill=skill,
                        title=f"{label}: {record.get('course_name')}",
                        source_ref=f"academic:{record.get('id')}",
                        directness=EvidenceDirectness.CONTEXTUAL,
                        summary=f"Course grade {record.get('grade')} supports foundational context; it does not independently verify the skill.",
                        metadata={
                            "course_name": record.get("course_name"),
                            "grade": record.get("grade"),
                            "institution": record.get("institution"),
                            "demo": bool(record.get("demo")),
                            "label": label,
                        },
                        created_at=now,
                    )
                )
        return output
