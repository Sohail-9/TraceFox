"""Postgres-backed persistence helpers for TraceFox integrations."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from services.shared.database import postgres_pool


class RepositoryStore:
    """Persist GitHub repository metadata and clone job status in Postgres."""

    def __init__(self) -> None:
        self._schema_ensured = False
        self._lock = asyncio.Lock()

    async def ensure_schema(self) -> None:
        if self._schema_ensured:
            return
        async with self._lock:
            if self._schema_ensured:
                return
            async with postgres_pool.connection() as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS github_tracked_repositories (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        repo_id BIGINT NOT NULL,
                        full_name TEXT NOT NULL,
                        description TEXT,
                        clone_url TEXT NOT NULL,
                        default_branch TEXT NOT NULL,
                        html_url TEXT NOT NULL,
                        private BOOLEAN NOT NULL DEFAULT FALSE,
                        clone_path TEXT,
                        sync_status TEXT NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, full_name)
                    );
                    """
                )
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS github_clone_jobs (
                        job_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        full_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        clone_path TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
            self._schema_ensured = True

    async def upsert_repository(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO github_tracked_repositories
                    (user_id, repo_id, full_name, description, clone_url, default_branch,
                     html_url, private, clone_path, sync_status, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NULL, $9, NOW())
                ON CONFLICT (user_id, full_name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    clone_url = EXCLUDED.clone_url,
                    default_branch = EXCLUDED.default_branch,
                    html_url = EXCLUDED.html_url,
                    private = EXCLUDED.private,
                    updated_at = NOW()
                RETURNING repo_id, full_name, description, clone_url, default_branch,
                          html_url, private, clone_path, sync_status, created_at, updated_at;
                """,
                user_id,
                data["repo_id"],
                data["full_name"],
                data.get("description"),
                data["clone_url"],
                data["default_branch"],
                data["html_url"],
                bool(data.get("private")),
                data.get("sync_status", "pending"),
            )
        return self._normalise_repo_row(record)

    async def update_repository_clone_status(
        self,
        user_id: str,
        full_name: str,
        *,
        clone_path: Optional[str],
        sync_status: str,
    ) -> None:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            await conn.execute(
                """
                UPDATE github_tracked_repositories
                SET clone_path = $1,
                    sync_status = $2,
                    updated_at = NOW()
                WHERE user_id = $3 AND full_name = $4;
                """,
                clone_path,
                sync_status,
                user_id,
                full_name,
            )

    async def list_repositories(self, user_id: str) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT repo_id, full_name, description, clone_url, default_branch, html_url,
                       private, clone_path, sync_status, created_at, updated_at
                FROM github_tracked_repositories
                WHERE user_id = $1
                ORDER BY full_name ASC;
                """,
                user_id,
            )
        return [self._normalise_repo_row(row) for row in rows]

    async def get_repository(self, user_id: str, full_name: str) -> Optional[Dict[str, Any]]:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT repo_id, full_name, description, clone_url, default_branch, html_url,
                       private, clone_path, sync_status, created_at, updated_at
                FROM github_tracked_repositories
                WHERE user_id = $1 AND full_name = $2;
                """,
                user_id,
                full_name,
            )
        return self._normalise_repo_row(row) if row else None

    def _normalise_repo_row(self, row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        data = dict(row)
        created = data.get("created_at")
        updated = data.get("updated_at")
        if created is not None:
            data["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created)
        if updated is not None:
            data["updated_at"] = updated.isoformat() if hasattr(updated, "isoformat") else str(updated)
        return data

    async def create_clone_job(self, job_id: str, user_id: str, full_name: str, status: str) -> None:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO github_clone_jobs (job_id, user_id, full_name, status, message, clone_path, updated_at)
                VALUES ($1, $2, $3, $4, NULL, NULL, NOW())
                ON CONFLICT (job_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = NOW();
                """,
                job_id,
                user_id,
                full_name,
                status,
            )

    async def update_clone_job(
        self,
        job_id: str,
        *,
        status: str,
        message: Optional[str] = None,
        clone_path: Optional[str] = None,
    ) -> None:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            await conn.execute(
                """
                UPDATE github_clone_jobs
                SET status = $1,
                    message = $2,
                    clone_path = $3,
                    updated_at = NOW()
                WHERE job_id = $4;
                """,
                status,
                message,
                clone_path,
                job_id,
            )

    async def list_clone_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        async with postgres_pool.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT job_id, full_name, status, message, clone_path, created_at, updated_at
                FROM github_clone_jobs
                WHERE user_id = $1
                ORDER BY updated_at DESC;
                """,
                user_id,
            )
        payload: List[Dict[str, Any]] = []
        for row in rows:
            entry = dict(row)
            created = entry.get("created_at")
            updated = entry.get("updated_at")
            if created is not None:
                entry["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created)
            if updated is not None:
                entry["updated_at"] = updated.isoformat() if hasattr(updated, "isoformat") else str(updated)
            payload.append(entry)
        return payload


repository_store = RepositoryStore()

__all__ = ["RepositoryStore", "repository_store"]
