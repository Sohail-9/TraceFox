from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

import httpx
import jwt

from services.shared.config import ConfigurationError, get_settings
from services.shared.models import Finding

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

    async def publish(
        self,
        *,
        repo_url: str,
        pr_number: int,
        head_sha: Optional[str],
        findings: List[Finding],
        summary_text: str,
        is_summary_only: bool = False,
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
            if is_summary_only:
                await self._post_pr_comment(owner, repo, pr_number, summary_text)
                return

            comments = self._build_inline_comments(findings)
            if comments:
                await self._create_review(owner, repo, pr_number, summary_text, comments)
            if head_sha:
                # Optional check run summary
                await self._create_check_run(owner, repo, head_sha, title="TraceFox Review", summary=summary_text)
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

    def _build_inline_comments(self, findings: List[Finding]) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        for f in findings[:50]:  # cap to a sensible batch
            # We do not have diff positions yet; use a safe fallback: position=1
            body = self._format_comment_body(f)
            comments.append({"path": f.file_path, "position": max(1, int(f.line_number) if f.line_number else 1), "body": body})
        return comments

    def _format_comment_body(self, f: Finding) -> str:
        severity = f.severity.value.upper() if hasattr(f.severity, "value") else str(f.severity).upper()
        type_label = f.type.value if hasattr(f.type, "value") else str(f.type)
        header = f"[{severity}] {type_label}:"
        lines = [header, f.message]
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
        confidence = float(f.confidence or 0.0)
        lines.append(f"Confidence: {confidence:.2f}")
        return "\n".join(lines)

    async def _get_auth_headers(self, owner: str, repo: str) -> Mapping[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._auth.token:
            headers["Authorization"] = f"Bearer {self._auth.token}"
            return headers

        if self._auth.app_id and self._auth.private_key_pem:
            token = await self._get_installation_token(owner, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def _generate_jwt(self) -> str:
        if not self._auth.app_id or not self._auth.private_key_pem:
            return ""
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self._auth.app_id,
        }
        return jwt.encode(payload, self._auth.private_key_pem, algorithm="RS256")

    async def _get_installation_token(self, owner: str, repo: str) -> Optional[str]:
        jwt_token = self._generate_jwt()
        if not jwt_token:
            return None

        installation_url = f"{self._auth.api_base}/repos/{owner}/{repo}/installation"
        async with httpx.AsyncClient() as client:
            resp = await client.get(installation_url, headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"})
            if resp.status_code != 200:
                logger.warning("Failed to get installation for %s/%s: %s", owner, repo, resp.status_code)
                return None
            installation_id = resp.json().get("id")

            access_token_url = f"{self._auth.api_base}/app/installations/{installation_id}/access_tokens"
            resp = await client.post(access_token_url, headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"})
            if resp.status_code != 201:
                logger.warning("Failed to get access token: %s", resp.status_code)
                return None
            return resp.json().get("token")

    async def update_comment(self, owner: str, repo: str, comment_id: int, body: str) -> None:
        """Update an existing comment body."""
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/issues/comments/{comment_id}"
        payload = {"body": body}
        await self._post(url, json=payload, owner=owner, repo=repo, method="PATCH")

    async def _post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> int:
        """Post a comment and return its ID."""
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        payload = {"body": body}
        resp = await self._post(url, json=payload, owner=owner, repo=repo)
        if resp and "id" in resp:
            return int(resp["id"])
        return 0

    async def post_reply(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment_id: int,
        body: str,
    ) -> None:
        """Post a reply to an existing PR comment thread."""
        if not self._enabled:
            return

        # PR replies (review comments) use a specific nested endpoint
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies"
        payload = {"body": body}
        await self._post(url, json=payload, owner=owner, repo=repo)


    async def _create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        summary: str,
        comments: List[Dict[str, Any]],
    ) -> None:
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {"event": "COMMENT", "body": summary, "comments": comments}
        await self._post(url, json=payload, owner=owner, repo=repo)

    async def _create_check_run(self, owner: str, repo: str, head_sha: str, *, title: str, summary: str) -> None:
        url = f"{self._auth.api_base}/repos/{owner}/{repo}/check-runs"
        payload = {
            "name": "TraceFox Review",
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": title, "summary": summary},
        }
        await self._post(url, json=payload, owner=owner, repo=repo)

    async def _post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        method: str = "POST",
    ) -> Optional[Dict[str, Any]]:
        try:
            headers = await self._get_auth_headers(owner or "", repo or "")
            async with httpx.AsyncClient(timeout=10) as client:
                if method == "PATCH":
                    resp = await client.patch(url, headers=headers, json=json)
                else:
                    resp = await client.post(url, headers=headers, json=json)
                
                if resp.status_code >= 400:
                    logger.warning("GitHub API %s failed: %s %s", url, resp.status_code, resp.text[:300])
                    return None
                return resp.json()
        except Exception as exc:  # pragma: no cover
            logger.warning("GitHub API call error: %s", exc)
            return None


publisher = GitHubPublisher()

__all__ = ["GitHubPublisher", "publisher"]
