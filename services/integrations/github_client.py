"""GitHub REST API helpers used across TraceFox services."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from services.shared.auth import AuthError

logger = logging.getLogger(__name__)

GITHUB_ACCEPT = "application/vnd.github+json"


async def _request(
    method: str,
    url: str,
    token: str,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}", "Accept": GITHUB_ACCEPT}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, params=params, headers=headers)
            if response.status_code == 401:
                raise AuthError("GitHub token is not authorised to perform this action")
            if response.status_code >= 400:
                text = response.text[:512]
                raise AuthError(f"GitHub API call failed ({response.status_code}): {text}")
            return response
    except httpx.RequestError as exc:
        raise AuthError(f"Unable to reach GitHub API ({exc})") from exc


async def list_repositories(
    token: str,
    *,
    api_base: str,
    per_page: int = 50,
    max_pages: int = 5,
) -> List[Dict[str, Any]]:
    """Return repositories accessible to the authenticated user."""

    url = f"{api_base}/user/repos"
    repos: List[Dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        params = {
            "per_page": per_page,
            "page": page,
            "affiliation": "owner,collaborator,organization_member",
            "sort": "full_name",
            "direction": "asc",
        }
        response = await _request("GET", url, token, params=params)
        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return repos


async def get_repository(token: str, *, api_base: str, full_name: str) -> Dict[str, Any]:
    url = f"{api_base}/repos/{full_name}"
    response = await _request("GET", url, token)
    data = response.json()
    if not isinstance(data, dict):
        raise AuthError("GitHub returned an unexpected response for repository lookup")
    return data


async def get_user(token: str, *, api_base: str) -> Dict[str, Any]:
    url = f"{api_base}/user"
    response = await _request("GET", url, token)
    data = response.json()
    if not isinstance(data, dict):
        raise AuthError("GitHub returned an unexpected response for user lookup")
    return data


__all__ = ["list_repositories", "get_repository", "get_user"]
