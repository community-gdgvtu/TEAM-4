from __future__ import annotations

import httpx
import pytest

from backend.services.github_service import GitHubService, GitHubServiceError


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/openai/example", ("openai", "example")),
        ("https://www.github.com/example-owner/example_repo.git", ("example-owner", "example_repo")),
    ],
)
def test_repository_url_parser_accepts_only_expected_github_shape(url, expected):
    assert GitHubService.parse_repository_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repository",
        "https://github.example/owner/repository",
        "https://127.0.0.1/owner/repository",
        "https://github.com/owner/repository/extra",
        "https://token@github.com/owner/repository",
        "https://github.com:444/owner/repository",
        "https://github.com/owner/%2e%2e",
    ],
)
def test_repository_url_parser_rejects_ssrf_and_ambiguous_urls(url):
    with pytest.raises(GitHubServiceError):
        GitHubService.parse_repository_url(url)


def test_live_failure_returns_safe_message_without_token(monkeypatch):
    secret = "github-token-must-not-appear"

    def fail_client(*args, **kwargs):
        raise RuntimeError(f"provider failed while using {secret}")

    monkeypatch.setattr(httpx, "Client", fail_client)

    with pytest.raises(GitHubServiceError) as captured:
        GitHubService(token=secret).analyze("https://github.com/owner/repository")

    assert str(captured.value) == "Live GitHub analysis failed safely; use demo evidence."
    assert secret not in str(captured.value)
