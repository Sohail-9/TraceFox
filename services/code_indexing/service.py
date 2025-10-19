from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from services.shared.event_bus import event_bus


class IndexingRequest(BaseModel):
    repository_id: str
    repo_url: str
    branch: str = "main"
    webhook_secret: Optional[str] = None
    incremental: bool = False
    changed_files: List[str] = Field(default_factory=list)


@dataclass
class IndexingJob:
    job_id: str
    repository_id: str
    status: str = "queued"
    indexed_files: int = 0
    graph_nodes: int = 0
    embeddings_generated: int = 0
    duration_seconds: float = 0.0


class CodebaseIndexingService:
    """Simulated codebase indexing pipeline hooking into Neo4j and a vector store."""

    def __init__(self) -> None:
        self._jobs: Dict[str, IndexingJob] = {}
        self._queue: asyncio.Queue[IndexingJob] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task[None]] = None

    async def queue_indexing(self, request: IndexingRequest) -> IndexingJob:
        await self._ensure_worker()
        job = IndexingJob(job_id=str(uuid4()), repository_id=request.repository_id)
        self._jobs[job.job_id] = job
        await self._queue.put(job)
        await event_bus.publish(
            "indexing:queued", {"job_id": job.job_id, "repository_id": request.repository_id}
        )
        logging.getLogger(__name__).info("Queued indexing job %s", job.job_id)
        return job

    async def get_job(self, job_id: str) -> Optional[IndexingJob]:
        return self._jobs.get(job_id)

    async def _worker(self) -> None:
        logger = logging.getLogger(__name__)
        while True:
            job = await self._queue.get()
            try:
                job.status = "running"
                await event_bus.publish("indexing:started", {"job_id": job.job_id})
                await asyncio.sleep(random.uniform(0.1, 0.5))
                job.indexed_files = random.randint(10, 200)
                job.graph_nodes = job.indexed_files * 5
                job.embeddings_generated = job.indexed_files * 3
                job.duration_seconds = round(random.uniform(1.0, 3.0), 2)
                job.status = "completed"
                await event_bus.publish(
                    "indexing:completed",
                    {
                        "job_id": job.job_id,
                        "repository_id": job.repository_id,
                        "indexed_files": job.indexed_files,
                    },
                )
                logger.debug("Completed indexing job %s", job.job_id)
            except Exception as exc:  # pragma: no cover - resiliency stub
                job.status = "failed"
                logger.exception("Indexing job %s failed: %s", job.job_id, exc)
            finally:
                self._queue.task_done()

    async def _ensure_worker(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        loop = asyncio.get_running_loop()
        self._worker_task = loop.create_task(self._worker(), name="indexing-worker")
