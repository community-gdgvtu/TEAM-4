"""Bounded GitHub REST ingestion for public repositories or optional token access."""

from __future__ import annotations

import base64
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse


class GitHubServiceError(ValueError):
    pass


class GitHubService:
    MAX_TREE_ENTRIES = 1_000
    MAX_FILES = 18
    MAX_FILE_BYTES = 64_000
    MAX_COMMITS = 6

    def __init__(self, token: str | None = None):
        self.token = token

    @staticmethod
    def parse_repository_url(repository_url: str) -> tuple[str, str]:
        parsed = urlparse(repository_url.strip())
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"github.com", "www.github.com"}
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
        ):
            raise GitHubServiceError("Enter an https://github.com/owner/repository URL.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            raise GitHubServiceError("Repository URL must contain only owner and repository.")
        owner, repository = parts
        repository = repository.removesuffix(".git")
        if not owner.replace("-", "").isalnum() or not repository.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise GitHubServiceError("Repository URL contains unsupported characters.")
        return owner, repository

    @staticmethod
    def _interesting(path: str) -> bool:
        name = PurePosixPath(path).name.lower()
        return name in {
            "requirements.txt", "pyproject.toml", "package.json", "dockerfile",
            "docker-compose.yml", "docker-compose.yaml", "firebase.json", ".firebaserc",
        } or PurePosixPath(path).suffix.lower() in {".py", ".sql", ".js", ".jsx", ".ts", ".tsx"}

    @staticmethod
    def _priority(path: str) -> tuple[int, str]:
        lowered = path.lower()
        name = PurePosixPath(lowered).name
        if name in {"requirements.txt", "pyproject.toml", "package.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
            return (0, lowered)
        if "/test" in f"/{lowered}" or name.startswith("test_"):
            return (1, lowered)
        if any(part in lowered for part in ("route", "api", "main", "model", "schema")):
            return (2, lowered)
        return (3, lowered)

    def analyze(
        self,
        repository_url: str,
        username: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        owner, repository = self.parse_repository_url(repository_url)
        try:
            import httpx
        except ImportError as exc:
            raise GitHubServiceError("Live GitHub analysis is unavailable; use demo evidence.") from exc

        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        base = f"https://api.github.com/repos/{owner}/{repository}"
        try:
            with httpx.Client(headers=headers, timeout=8.0, follow_redirects=False) as client:
                repo_response = client.get(base)
                if repo_response.status_code == 404:
                    raise GitHubServiceError("Repository was not found or is private without a token.")
                if repo_response.status_code in {403, 429}:
                    raise GitHubServiceError("GitHub rate limit reached; use demo evidence.")
                repo_response.raise_for_status()
                metadata = repo_response.json()
                selected_branch = branch or metadata.get("default_branch") or "main"
                tree_response = client.get(f"{base}/git/trees/{selected_branch}", params={"recursive": "1"})
                tree_response.raise_for_status()
                tree = tree_response.json().get("tree", [])[: self.MAX_TREE_ENTRIES]
                paths = sorted(
                    [item["path"] for item in tree if item.get("type") == "blob" and self._interesting(item.get("path", ""))],
                    key=self._priority,
                )[: self.MAX_FILES]
                files = []
                for path in paths:
                    response = client.get(f"{base}/contents/{path}", params={"ref": selected_branch})
                    if response.status_code != 200:
                        continue
                    payload = response.json()
                    if payload.get("encoding") != "base64" or int(payload.get("size", 0)) > self.MAX_FILE_BYTES:
                        continue
                    try:
                        content = base64.b64decode(payload.get("content", ""), validate=False).decode("utf-8")
                    except (ValueError, UnicodeDecodeError):
                        continue
                    files.append({"path": path, "content": content[: self.MAX_FILE_BYTES]})

                params: dict[str, str | int] = {"per_page": self.MAX_COMMITS}
                if username:
                    params["author"] = username
                commits_response = client.get(f"{base}/commits", params=params)
                commits = []
                if commits_response.status_code == 200:
                    for item in commits_response.json()[: self.MAX_COMMITS]:
                        paths_for_commit: list[str] = []
                        detail = client.get(f"{base}/commits/{item.get('sha')}")
                        if detail.status_code == 200:
                            paths_for_commit = [entry.get("filename", "") for entry in detail.json().get("files", [])[:30]]
                        commit = item.get("commit", {})
                        author = item.get("author") or {}
                        commits.append({
                            "sha": str(item.get("sha", ""))[:12],
                            "author_login": author.get("login"),
                            "message": str(commit.get("message", "")).splitlines()[0][:240],
                            "date": (commit.get("author") or {}).get("date"),
                            "paths": paths_for_commit,
                        })
        except GitHubServiceError:
            raise
        except Exception as exc:
            raise GitHubServiceError("Live GitHub analysis failed safely; use demo evidence.") from exc

        return {
            "id": f"REPO-LIVE-{owner}-{repository}",
            "repository_url": repository_url,
            "owner": owner,
            "name": repository,
            "branch": selected_branch,
            "description": metadata.get("description") or "GitHub repository",
            "is_demo_snapshot": False,
            "files": files,
            "commits": commits,
            "bounded": {"files": len(files), "commits": len(commits), "tree_entries_examined": len(tree)},
        }
