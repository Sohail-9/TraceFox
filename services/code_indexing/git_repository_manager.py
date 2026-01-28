"""Manage Git repository clones and metadata for TraceFox."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from services.code_indexing.service import CodebaseIndexingService, IndexingRequest
from services.shared.persistence import RepositoryStore, repository_store

logger = logging.getLogger(__name__)


def _default_storage_path() -> Path:
    root = os.environ.get("TRACEFOX_REPO_STORAGE_PATH")
    if root:
        return Path(root)
    return Path.cwd() / "data" / "repos"


class GitRepositoryManager:
    """Coordinates clone jobs and kicks off indexing runs."""

    def __init__(
        self,
        *,
        store: RepositoryStore | None = None,
        indexing_service: CodebaseIndexingService,
        storage_path: Optional[Path] = None,
    ) -> None:
        self._store = store or repository_store
        self._indexing = indexing_service
        self._storage_path = storage_path or _default_storage_path()
        self._simulate = (os.environ.get("TRACEFOX_ENABLE_ACTUAL_CLONE", "true").lower() != "true")
        self._tasks: set[asyncio.Task[Any]] = set()

    async def list_tracked(self, user_id: str) -> Dict[str, Any]:
        repositories = await self._store.list_repositories(user_id)
        clone_jobs = await self._store.list_clone_jobs(user_id)
        return {"repositories": repositories, "clone_jobs": clone_jobs}

    async def register_repository(
        self,
        user_id: str,
        repo_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "repo_id": repo_data["id"],
            "full_name": repo_data["full_name"],
            "description": repo_data.get("description"),
            "clone_url": repo_data.get("clone_url") or repo_data.get("html_url"),
            "default_branch": repo_data.get("default_branch") or "main",
            "html_url": repo_data.get("html_url"),
            "private": bool(repo_data.get("private")),
            "sync_status": "queued",
        }
        record = await self._store.upsert_repository(user_id, payload)
        return record

    async def schedule_clone(
        self,
        *,
        user_id: str,
        repo_data: Dict[str, Any],
        github_token: str,
    ) -> Dict[str, Any]:
        job_id = str(uuid4())
        full_name = repo_data["full_name"]
        await self._store.create_clone_job(job_id, user_id, full_name, "queued")
        await self._store.update_repository_clone_status(user_id, full_name, clone_path=None, sync_status="queued")
        task = asyncio.create_task(
            self._run_clone_job(job_id=job_id, user_id=user_id, repo_data=repo_data, token=github_token),
            name=f"repo-clone-{job_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return {"job_id": job_id, "status": "queued"}

    async def _run_clone_job(self, job_id: str, user_id: str, repo_data: Dict[str, Any], token: str) -> None:
        full_name = repo_data["full_name"]
        try:
            target_dir = self._storage_path / user_id / full_name.replace("/", "__")
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            if self._simulate:
                await asyncio.sleep(random.uniform(0.1, 0.3))
                metadata_path = target_dir / "TRACEFOX_REPO.json"
                target_dir.mkdir(parents=True, exist_ok=True)
                metadata = {
                    "full_name": full_name,
                    "clone_url": repo_data.get("clone_url"),
                    "default_branch": repo_data.get("default_branch"),
                    "html_url": repo_data.get("html_url"),
                    "simulated": True,
                }
                metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                await asyncio.sleep(random.uniform(0.05, 0.2))
            else:
                await self._run_git_clone(repo_data=repo_data, token=token, target_dir=target_dir)

            await self._store.update_clone_job(
                job_id,
                status="completed",
                message=None,
                clone_path=str(target_dir),
            )
            await self._store.update_repository_clone_status(
                user_id,
                full_name,
                clone_path=str(target_dir),
                sync_status="cloned",
            )
            await self._queue_indexing_job(repo_data)
            logger.info("Repository %s cloned for user %s", full_name, user_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Clone job %s failed: %s", job_id, exc)
            await self._store.update_clone_job(
                job_id,
                status="failed",
                message=str(exc),
                clone_path=None,
            )
            await self._store.update_repository_clone_status(
                user_id,
                full_name,
                clone_path=None,
                sync_status="failed",
            )

    async def _run_git_clone(self, *, repo_data: Dict[str, Any], token: str, target_dir: Path) -> None:
        import subprocess

        clone_url = repo_data.get("clone_url")
        if not clone_url:
            raise RuntimeError("Repository does not expose a clone url")
        if target_dir.exists():
            return
        auth_url = clone_url.replace("https://", f"https://{token}@")
        logger.debug("Cloning repository %s into %s", repo_data["full_name"], target_dir)
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            auth_url,
            str(target_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode().strip() or stdout.decode().strip()}")

    async def _queue_indexing_job(self, repo_data: Dict[str, Any]) -> None:
        repository_id = str(repo_data.get("id"))
        repo_url = repo_data.get("html_url") or repo_data.get("clone_url")
        if not repo_url:
            return
        request = IndexingRequest(repository_id=repository_id, repo_url=repo_url, branch=repo_data.get("default_branch") or "main")
        await self._indexing.queue_indexing(request)

    async def get_repository(self, user_id: str, full_name: str) -> Optional[Dict[str, Any]]:
        return await self._store.get_repository(user_id, full_name)


__all__ = ["GitRepositoryManager"]
