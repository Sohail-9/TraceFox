from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

import httpx

from services.shared.config import ConfigurationError, get_settings
from services.shared.models import ReviewFinding

logger = logging.getLogger(__name__)


@dataclass
class GitHubAuth:
    api_base: str
    token: Optional[str]
    app_id: Optional[str]
    private_key_pem: Optional[str]


class GitHubPublisher:
    """Publishes TraceFox review output to GitHub as an inline review and a check run.

    This implementation is resilient to missing credentials and will no-op when
    publishing is disabled via configuration. Network failures are logged and
    swallowed so they never block the main review workflow.
    """

    def __init__(self) -> None:
        self._enabled = False
        self._auth = GitHubAuth(api_base="https://api.github.com", token=None, app_id=None, private_key_pem=None)
        try:
            cfg = get_settings()
            gh = getattr(cfg, "github", None)
            if gh is None:
                self._enabled = False
                return
            self._enabled = bool(getattr(gh, "publish_enabled", False))
            self._auth = GitHubAuth(
                api_base=str(getattr(gh, "api_base", "https://api.github.com") or "https://api.github.com"),
                token=getattr(gh, "token", None),
                app_id=str(getattr(gh, "app_id", None)) if getattr(gh, "app_id", None) is not None else None,
                private_key_pem=getattr(gh, "private_key_pem", None),
            )
        except ConfigurationError:
            self._enabled = False

    def enabled(self) -> bool:
        return self._enabled

    def publish(
        self,
        *,
        repo_url: str,
        pr_number: int,
        head_sha: Optional[str],
        findings: List[ReviewFinding],
        summary_text: str,
    ) -> None:
        if not self._enabled:
            logger.debug("GitHub publishing disabled; skipping")
            return
        try:
            owner, repo = self._parse_repo_url(repo_url)
        except ValueError as exc:
            logger.warning("Unable to parse repository from %s: %s", repo_url, exc)
            return

        try:
            comments = self._build_inline_comments(findings)
            if comments:
                self._create_review(owner, repo, pr_number, summary_text, comments)
            if head_sha:
                # Optional check run summary
                self._create_check_run(owner, repo, head_sha, title="TraceFox Review", summary=summary_text)
        except Exception as exc:  # pragma: no cover - network/hard failure path
            logger.error("GitHub publish failed: %s", exc, exc_info=True)

    # ---------- internals ----------

    def _parse_repo_url(self, url: str) -> Tuple[str, str]:
        # Accept https://github.com/owner/repo(.git)?
        parts = url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("invalid url")
        owner = parts[-2]
        repo = parts[-1].removesuffix(".git")
        if not owner or not repo:
            raise ValueError("missing owner/repo")
        return owner, repo

    def _build_inline_comments(self, findings: List[ReviewFinding]) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        for f in findings[:50]:  # cap to a sensible batch
            # We do not have diff positions yet; use a safe fallback: position=1
            body = self._format_comment_body(f)
            comments.append({"path": f.file_path, "position": max(1, int(f.line_number) if f.line_number else 1), "body": body})
        return comments

    def _format_comment_body(self, f: ReviewFinding) -> str:
        header = f"[{f.severity.upper()}] {f.category}:"
        lines = [header, f.description]
        if f.suggested_fix:
            lines.append("")
            lines.append("Suggested change:")
            lines.append("```suggestion")
            lines.append(f.suggested_fix)
            lines.append("```")
        if f.code_diff:
            lines.append("")
            lines.append("Context diff:")
            lines.append("```diff")
            lines.append(f.code_diff)
            lines.append("```")
        lines.append("")
        lines.append(f"Confidence: {f.confidence_score:.2f}")
        return "\n".join(lines)

    def _headers(self) -> Mapping[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._auth.token:
            headers["Authorization"] = f"Bearer {self._auth.token}"
        return headers

    def _create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        summary: str,
        comments: List[Dict[str, Any]],
    ) -> None:
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {"event": "COMMENT", "body": summary, "comments": comments}
        self._post(url, json=payload)

    def _create_check_run(self, owner: str, repo: str, head_sha: str, *, title: str, summary: str) -> None:
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/check-runs"
        payload = {
            "name": "TraceFox Review",
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": title, "summary": summary},
        }
        self._post(url, json=payload)

    def _post(self, url: str, *, json: Mapping[str, Any]) -> None:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, headers=self._headers(), json=json)
                if resp.status_code >= 400:
                    logger.warning("GitHub API %s failed: %s %s", url, resp.status_code, resp.text[:300])
        except Exception as exc:  # pragma: no cover
            logger.warning("GitHub API call error: %s", exc)


publisher = GitHubPublisher()

__all__ = ["GitHubPublisher", "publisher"]

