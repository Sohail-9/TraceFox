"""GitHub integration endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from services.api_gateway.routes.auth import require_user
from services.integrations import github_client
from services.shared.auth import AuthError, AuthenticatedUser
from services.shared.config import get_settings
from services.shared.models import (
    GitHubCloneJob,
    GitHubRepositorySummary,
    GitHubRepositoryTrackResponse,
    GitHubTrackedRepository,
)

router = APIRouter(prefix="/integrations/github", tags=["github"])


class RepositoryListResponse(BaseModel):
    repositories: List[GitHubRepositorySummary]


class TrackRepositoryRequest(BaseModel):
    full_name: str


class TrackedRepositoryResponse(BaseModel):
    repository: GitHubTrackedRepository
    clone_job: dict


class TrackedResourcesResponse(BaseModel):
    repositories: List[GitHubTrackedRepository]
    clone_jobs: List[GitHubCloneJob]


def _registry_dependency():
    from services.api_gateway.main import get_registry as _get_registry

    return _get_registry()


async def _github_api_base() -> str:
    settings = get_settings()
    gh = getattr(settings, "github", None)
    if isinstance(gh, dict):
        return gh.get("api_base") or "https://api.github.com"
    return getattr(gh, "api_base", "https://api.github.com")


@router.get("/repos", response_model=RepositoryListResponse)
async def list_repositories(
    current_user: AuthenticatedUser = Depends(require_user),
) -> RepositoryListResponse:
    token = current_user.github_access_token
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "GitHub token not available for this user")
    api_base = await _github_api_base()
    try:
        repos_raw = await github_client.list_repositories(token, api_base=api_base)
    except AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    summaries = [
        GitHubRepositorySummary(
            id=repo["id"],
            full_name=repo["full_name"],
            description=repo.get("description"),
            clone_url=repo.get("clone_url") or repo.get("html_url"),
            default_branch=repo.get("default_branch") or "main",
            html_url=repo.get("html_url"),
            private=bool(repo.get("private")),
            owner={"login": repo.get("owner", {}).get("login", "")},
        )
        for repo in repos_raw
    ]
    return RepositoryListResponse(repositories=summaries)


@router.post("/repos", response_model=TrackedRepositoryResponse, status_code=status.HTTP_201_CREATED)
async def track_repository(
    payload: TrackRepositoryRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    registry=Depends(_registry_dependency),
) -> TrackedRepositoryResponse:
    token = current_user.github_access_token
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "GitHub token not available for this user")
    api_base = await _github_api_base()
    try:
        repo_data = await github_client.get_repository(token, api_base=api_base, full_name=payload.full_name)
    except AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    summary = GitHubRepositorySummary(
        id=repo_data["id"],
        full_name=repo_data["full_name"],
        description=repo_data.get("description"),
        clone_url=repo_data.get("clone_url") or repo_data.get("html_url"),
        default_branch=repo_data.get("default_branch") or "main",
        html_url=repo_data.get("html_url"),
        private=bool(repo_data.get("private")),
        owner={"login": repo_data.get("owner", {}).get("login", "")},
    )
    response = await registry.onboard_repository(current_user.user_id, token, summary)
    return TrackedRepositoryResponse(repository=response.repository, clone_job=response.clone_job)


@router.get("/tracked", response_model=TrackedResourcesResponse)
async def list_tracked(
    current_user: AuthenticatedUser = Depends(require_user),
    registry=Depends(_registry_dependency),
) -> TrackedResourcesResponse:
    payload = await registry.list_tracked_repositories(current_user.user_id)
    return TrackedResourcesResponse(
        repositories=[GitHubTrackedRepository.model_validate(item) for item in payload.get("repositories", [])],
        clone_jobs=[GitHubCloneJob.model_validate(item) for item in payload.get("clone_jobs", [])],
    )
