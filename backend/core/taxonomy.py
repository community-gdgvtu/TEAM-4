"""Deterministic skill vocabulary and explainable repository signals."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SignalRule:
    id: str
    source_kind: str
    path_pattern: str | None = None
    content_pattern: str | None = None
    directness: str = "DIRECT"
    title: str = "Source signal"
    summary: str = "Relevant source evidence was found."

    def path_matches(self, path: str) -> bool:
        return self.path_pattern is None or bool(
            re.search(self.path_pattern, path, re.IGNORECASE)
        )

    def content_matches(self, content: str) -> bool:
        return self.content_pattern is None or bool(
            re.search(self.content_pattern, content, re.IGNORECASE | re.MULTILINE)
        )


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    aliases: tuple[str, ...]
    academic_aliases: tuple[str, ...]
    challenge_template: str | None
    uncertainties: tuple[str, ...]
    rules: tuple[SignalRule, ...]


SKILLS: dict[str, SkillDefinition] = {
    "Python": SkillDefinition(
        name="Python",
        aliases=("python", "パイソン"),
        academic_aliases=("python", "programming", "algorithms"),
        challenge_template="python-normalize-records-v1",
        uncertainties=("Edge-case handling and deterministic data transformation",),
        rules=(
            SignalRule("python-source", "code", r"\.py$", r"\b(def|class)\s+\w+", "DIRECT", "Substantive Python source", "Functions or classes are implemented in Python."),
            SignalRule("python-tests", "test", r"(^|/)tests?/.*\.py$", r"\b(assert|pytest|TestClient)\b", "CORROBORATING", "Python tests", "Automated Python tests exercise the project."),
            SignalRule("python-deps", "dependency", r"(^|/)(requirements[^/]*\.txt|pyproject\.toml)$", r"[A-Za-z0-9_-]+", "CORROBORATING", "Python dependency manifest", "A Python dependency manifest is present."),
        ),
    ),
    "FastAPI": SkillDefinition(
        name="FastAPI",
        aliases=("fastapi", "fast api", "高速api"),
        academic_aliases=("api development", "web api", "backend"),
        challenge_template="fastapi-duplicate-email-v1",
        uncertainties=("Request validation and conflict-safe error handling",),
        rules=(
            SignalRule("fastapi-dependency", "dependency", r"(^|/)(requirements[^/]*\.txt|pyproject\.toml)$", r"\bfastapi\b", "CORROBORATING", "FastAPI dependency", "FastAPI is declared as a project dependency."),
            SignalRule("fastapi-app", "code", r"\.py$", r"\bFastAPI\s*\(", "DIRECT", "FastAPI application", "A FastAPI application is constructed in source."),
            SignalRule("fastapi-router", "code", r"\.py$", r"\bAPIRouter\s*\(|@\w+\.(get|post|put|patch|delete)\s*\(", "DIRECT", "API routes", "FastAPI router or route decorators are implemented."),
            SignalRule("fastapi-model", "code", r"\.py$", r"\bBaseModel\b", "CORROBORATING", "Request/response models", "Typed request or response models support the API."),
            SignalRule("fastapi-tests", "test", r"(^|/)tests?/.*\.py$", r"\b(TestClient|status_code)\b", "CORROBORATING", "FastAPI tests", "HTTP behavior is exercised by automated tests."),
        ),
    ),
    "SQL": SkillDefinition(
        name="SQL",
        aliases=("sql", "postgresql", "mysql", "database", "データベース", "データベース設計"),
        academic_aliases=("database", "sql", "relational", "data modelling"),
        challenge_template="sql-customer-orders-v1",
        uncertainties=("Correct joins, aggregation, and empty-result behavior",),
        rules=(
            SignalRule("sql-file", "code", r"\.sql$", r"\b(SELECT|CREATE\s+TABLE|JOIN|GROUP\s+BY)\b", "DIRECT", "SQL source", "SQL schema or query logic is present."),
            SignalRule("sql-query-code", "code", r"\.(py|js|ts)$", r"\b(SELECT|JOIN|GROUP\s+BY|sqlalchemy|create_engine)\b", "DIRECT", "Database query implementation", "Application source contains database query logic."),
            SignalRule("sql-tests", "test", r"(^|/)tests?/", r"\b(sql|database|query|sqlite)\b", "CORROBORATING", "Database tests", "Tests exercise database behavior."),
        ),
    ),
    "Docker": SkillDefinition(
        name="Docker",
        aliases=("docker", "container", "コンテナ"),
        academic_aliases=("cloud computing", "devops", "containers"),
        challenge_template=None,
        uncertainties=("Production-ready container configuration has not been demonstrated",),
        rules=(
            SignalRule("dockerfile", "code", r"(^|/)Dockerfile$", r"\b(FROM|CMD|ENTRYPOINT)\b", "DIRECT", "Dockerfile", "A container build definition is present."),
            SignalRule("compose", "code", r"(^|/)docker-compose\.ya?ml$", r"\bservices\s*:", "CORROBORATING", "Compose configuration", "A multi-service container configuration is present."),
        ),
    ),
    "Git": SkillDefinition(
        name="Git",
        aliases=("git", "github", "version control", "バージョン管理"),
        academic_aliases=("software engineering", "version control"),
        challenge_template=None,
        uncertainties=("Branching and collaboration practices are not execution-verified",),
        rules=(),
    ),
    "JavaScript": SkillDefinition(
        name="JavaScript",
        aliases=("javascript", "typescript", "ecmascript"),
        academic_aliases=("web development", "javascript"),
        challenge_template=None,
        uncertainties=("Runtime behavior has not been challenge-verified",),
        rules=(SignalRule("javascript-source", "code", r"\.(js|jsx|ts|tsx)$", r"\b(function|const|let|class|import)\b", "DIRECT", "JavaScript source", "Substantive JavaScript or TypeScript source is present."),),
    ),
    "React": SkillDefinition(
        name="React",
        aliases=("react", "react.js", "リアクト"),
        academic_aliases=("frontend", "user interface"),
        challenge_template=None,
        uncertainties=("Component behavior has not been challenge-verified",),
        rules=(
            SignalRule("react-dependency", "dependency", r"package\.json$", r"[\"']react[\"']", "CORROBORATING", "React dependency", "React is declared as a dependency."),
            SignalRule("react-source", "code", r"\.(jsx|tsx)$", r"\b(useState|useEffect|return\s*\()", "DIRECT", "React component source", "React component or hook usage is present."),
        ),
    ),
    "Node.js": SkillDefinition(
        name="Node.js",
        aliases=("node.js", "nodejs", "express", "express.js"),
        academic_aliases=("backend development", "server-side javascript"),
        challenge_template=None,
        uncertainties=("Server behavior has not been challenge-verified",),
        rules=(
            SignalRule("node-dependency", "dependency", r"package\.json$", r"[\"'](express|fastify|koa)[\"']", "CORROBORATING", "Node server dependency", "A Node server framework is declared."),
            SignalRule("node-server", "code", r"\.(js|ts)$", r"\b(express\s*\(|createServer\s*\(|app\.(get|post|put|delete)\s*\()", "DIRECT", "Node server source", "Node or Express server behavior is implemented."),
        ),
    ),
    "MongoDB": SkillDefinition(
        name="MongoDB",
        aliases=("mongodb", "mongo", "mongoose"),
        academic_aliases=("nosql", "document database", "mongodb"),
        challenge_template=None,
        uncertainties=("Database behavior has not been challenge-verified",),
        rules=(
            SignalRule("mongo-dependency", "dependency", r"(requirements[^/]*\.txt|pyproject\.toml|package\.json)$", r"\b(pymongo|motor|mongoose)\b", "CORROBORATING", "MongoDB dependency", "A MongoDB client dependency is declared."),
            SignalRule("mongo-client", "code", r"\.(py|js|ts)$", r"\b(MongoClient|mongoose\.connect|AsyncIOMotorClient)\b", "DIRECT", "MongoDB client usage", "Application source creates a MongoDB client."),
        ),
    ),
    "Firebase": SkillDefinition(
        name="Firebase",
        aliases=("firebase", "firestore"),
        academic_aliases=("firebase", "cloud application development"),
        challenge_template=None,
        uncertainties=("Firebase behavior has not been challenge-verified",),
        rules=(
            SignalRule("firebase-dependency", "dependency", r"(requirements[^/]*\.txt|package\.json)$", r"\b(firebase-admin|firebase)\b", "CORROBORATING", "Firebase dependency", "A Firebase SDK is declared."),
            SignalRule("firebase-api", "code", r"\.(py|js|ts)$", r"\b(initializeApp|getFirestore|firebase_admin|firestore\s*\()", "DIRECT", "Firebase API usage", "Application source invokes Firebase APIs."),
            SignalRule("firebase-config", "code", r"(^|/)(firebase\.json|\.firebaserc)$", r".+", "CORROBORATING", "Firebase configuration", "Firebase project configuration is present."),
        ),
    ),
    "Machine Learning": SkillDefinition(
        name="Machine Learning",
        aliases=("machine learning", "scikit-learn", "tensorflow", "pytorch", "機械学習"),
        academic_aliases=("machine learning", "artificial intelligence"),
        challenge_template=None,
        uncertainties=("Model evaluation quality has not been execution-verified",),
        rules=(SignalRule("ml-training", "code", r"\.py$", r"\b(sklearn|tensorflow|torch|\.fit\s*\()", "DIRECT", "Model training source", "Machine-learning training or evaluation code is present."),),
    ),
    "Japanese B1": SkillDefinition(
        name="Japanese B1",
        aliases=("japanese b1", "日本語b1", "日本語 b1", "日本語能力"),
        academic_aliases=("japanese", "日本語"),
        challenge_template=None,
        uncertainties=("Language level is supporting demo academic evidence only",),
        rules=(),
    ),
}


def normalize_skill(value: str) -> str | None:
    lowered = value.strip().lower()
    for definition in SKILLS.values():
        if lowered == definition.name.lower() or lowered in {
            alias.lower() for alias in definition.aliases
        }:
            return definition.name
    return None


def challenge_supported(skill: str) -> bool:
    definition = SKILLS.get(skill)
    return bool(definition and definition.challenge_template)
