"""Lightweight SQLite-backed persistence helpers for TraceFox integrations."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional


def _default_db_path() -> Path:
    root = os.environ.get("TRACEFOX_DATA_PATH")
    if root:
        path = Path(root)
        if path.is_dir():
            return path / "tracefox.db"
        return path
    return Path.cwd() / "data" / "tracefox.db"


_DB_PATH: Optional[Path] = None
_CONNECTION_LOCK = RLock()
_CONNECTION: Optional[sqlite3.Connection] = None


def _resolve_db_path() -> Path:
    global _DB_PATH
    env_path = os.environ.get("TRACEFOX_DATA_PATH")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_dir():
            candidate = candidate / "tracefox.db"
        _DB_PATH = candidate
    if _DB_PATH is None:
        _DB_PATH = _default_db_path()
    return _DB_PATH


def _ensure_parent_dir(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    global _CONNECTION
    if _CONNECTION is not None:
        return _CONNECTION
    with _CONNECTION_LOCK:
        if _CONNECTION is not None:
            return _CONNECTION
        path = _resolve_db_path()
        _ensure_parent_dir(path)
        conn = sqlite3.connect(
            path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        _CONNECTION = conn
        return conn


async def _execute_async(query: str, params: Iterable[Any] = ()) -> None:
    def runner() -> None:
        conn = _get_connection()
        conn.execute(query, tuple(params))
        conn.commit()

    await asyncio.to_thread(runner)


async def _fetchall_async(query: str, params: Iterable[Any] = ()) -> List[sqlite3.Row]:
    def runner() -> List[sqlite3.Row]:
        conn = _get_connection()
        cursor = conn.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return await asyncio.to_thread(runner)


async def _fetchone_async(query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    rows = await _fetchall_async(query, params)
    return rows[0] if rows else None


class RepositoryStore:
    """Persist GitHub repository metadata and clone job status."""

    def __init__(self) -> None:
        self._schema_ensured = False
        self._lock = asyncio.Lock()

    async def ensure_schema(self) -> None:
        if self._schema_ensured:
            return
        async with self._lock:
            if self._schema_ensured:
                return
            await _execute_async(
                """
                CREATE TABLE IF NOT EXISTS github_tracked_repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    repo_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    description TEXT,
                    clone_url TEXT NOT NULL,
                    default_branch TEXT NOT NULL,
                    html_url TEXT NOT NULL,
                    private INTEGER NOT NULL,
                    clone_path TEXT,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, full_name)
                );
                """
            )
            await _execute_async(
                """
                CREATE TABLE IF NOT EXISTS github_clone_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    clone_path TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._schema_ensured = True

    async def upsert_repository(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_schema()
        await _execute_async(
            """
            INSERT INTO github_tracked_repositories
                (user_id, repo_id, full_name, description, clone_url, default_branch, html_url, private, clone_path, sync_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, full_name)
            DO UPDATE SET
                description=excluded.description,
                clone_url=excluded.clone_url,
                default_branch=excluded.default_branch,
                html_url=excluded.html_url,
                private=excluded.private,
                updated_at=CURRENT_TIMESTAMP;
            """,
            (
                user_id,
                data["repo_id"],
                data["full_name"],
                data.get("description"),
                data["clone_url"],
                data["default_branch"],
                data["html_url"],
                1 if data.get("private") else 0,
                data.get("clone_path"),
                data.get("sync_status", "pending"),
            ),
        )
        return await self.get_repository(user_id, data["full_name"])  # type: ignore[return-value]

    async def update_repository_clone_status(
        self,
        user_id: str,
        full_name: str,
        *,
        clone_path: Optional[str],
        sync_status: str,
    ) -> None:
        await self.ensure_schema()
        await _execute_async(
            """
            UPDATE github_tracked_repositories
            SET clone_path = ?, sync_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND full_name = ?;
            """,
            (clone_path, sync_status, user_id, full_name),
        )

    async def list_repositories(self, user_id: str) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        rows = await _fetchall_async(
            """
            SELECT repo_id, full_name, description, clone_url, default_branch, html_url,
                   private, clone_path, sync_status, created_at, updated_at
            FROM github_tracked_repositories
            WHERE user_id = ?
            ORDER BY full_name ASC;
            """,
            (user_id,),
        )
        return [self._normalise_repo_row(row) for row in rows]

    async def get_repository(self, user_id: str, full_name: str) -> Optional[Dict[str, Any]]:
        await self.ensure_schema()
        row = await _fetchone_async(
            """
            SELECT repo_id, full_name, description, clone_url, default_branch, html_url,
                   private, clone_path, sync_status, created_at, updated_at
            FROM github_tracked_repositories
            WHERE user_id = ? AND full_name = ?;
            """,
            (user_id, full_name),
        )
        return self._normalise_repo_row(row) if row else None

    def _normalise_repo_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["private"] = bool(data.get("private"))
        return data

    async def create_clone_job(self, job_id: str, user_id: str, full_name: str, status: str) -> None:
        await self.ensure_schema()
        await _execute_async(
            """
            INSERT OR REPLACE INTO github_clone_jobs
                (job_id, user_id, full_name, status, message, clone_path, updated_at)
            VALUES (?, ?, ?, ?, NULL, NULL, CURRENT_TIMESTAMP);
            """,
            (job_id, user_id, full_name, status),
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
        await _execute_async(
            """
            UPDATE github_clone_jobs
            SET status = ?, message = ?, clone_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?;
            """,
            (status, message, clone_path, job_id),
        )

    async def list_clone_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        rows = await _fetchall_async(
            """
            SELECT job_id, full_name, status, message, clone_path, created_at, updated_at
            FROM github_clone_jobs
            WHERE user_id = ?
            ORDER BY updated_at DESC;
            """,
            (user_id,),
        )
        return [dict(row) for row in rows]


repository_store = RepositoryStore()

__all__ = ["RepositoryStore", "repository_store"]
