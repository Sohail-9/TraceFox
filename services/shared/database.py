"""Connection factories and helpers for durable service dependencies."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from threading import RLock
from typing import AsyncIterator, List, Optional, Sequence

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncSession
from redis.asyncio import Redis

from services.shared.config import ConfigurationError, QdrantCollectionSettings, get_settings

try:  # Optional dependency - some testing environments mock vector storage
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as qdrant_models  # type: ignore
    from qdrant_client.http.api_client import UnexpectedResponse  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - makes local tooling resilient without qdrant-client
    QdrantClient = None  # type: ignore
    qdrant_models = None  # type: ignore


class PostgresPool:
    """Asyncpg-based connection pool configured via central settings."""

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._statement_timeout_ms: Optional[int] = None

    async def _configure_connection(self, connection: asyncpg.Connection) -> None:
        if self._statement_timeout_ms is None:
            cfg = get_settings().postgres
            self._statement_timeout_ms = int(cfg.statement_timeout_seconds * 1000)
        await connection.execute(f"SET statement_timeout = {self._statement_timeout_ms}")

    async def init(self) -> None:
        if self._pool is not None:
            return
        async with self._lock:
            if self._pool is not None:
                return
            cfg = get_settings().postgres
            self._statement_timeout_ms = int(cfg.statement_timeout_seconds * 1000)
            self._pool = await asyncpg.create_pool(
                host=cfg.host,
                port=cfg.port,
                user=cfg.user,
                password=cfg.password,
                database=cfg.database,
                min_size=cfg.min_pool,
                max_size=cfg.max_pool,
                timeout=cfg.connection_timeout_seconds,
                command_timeout=cfg.statement_timeout_seconds,
                max_inactive_connection_lifetime=cfg.max_idle_seconds,
                init=self._configure_connection,
            )

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        if self._pool is None:
            await self.init()
        assert self._pool is not None  # nosec: internal guard ensuring pool initialised
        async with self._pool.acquire() as conn:
            yield conn

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


class RedisPool:
    """Lazily instantiated Redis client honouring configuration-driven limits."""

    def __init__(self) -> None:
        self._client: Optional[Redis] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> Redis:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            cfg = get_settings().redis
            self._client = Redis(
                host=cfg.host,
                port=cfg.port,
                username=cfg.username,
                password=cfg.password,
                db=cfg.db,
                max_connections=cfg.max_connections,
                socket_timeout=cfg.socket_timeout_seconds,
                socket_connect_timeout=cfg.socket_timeout_seconds,
                decode_responses=False,
            )
            return self._client

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise ConfigurationError("Redis client not initialised; call await redis_pool.connect()")
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


class Neo4jDriver:
    """Async Neo4j driver wrapper with connection pooling."""

    def __init__(self) -> None:
        self._driver = None
        self._lock = asyncio.Lock()

    async def _ensure_driver(self) -> None:
        if self._driver is not None:
            return
        async with self._lock:
            if self._driver is not None:
                return
            cfg = get_settings().neo4j
            self._driver = AsyncGraphDatabase.driver(
                cfg.uri,
                auth=(cfg.user, cfg.password),
                max_connection_pool_size=cfg.max_connection_pool_size,
                connection_timeout=cfg.acquisition_timeout_seconds,
                encrypted=cfg.encrypted,
            )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        await self._ensure_driver()
        assert self._driver is not None  # nosec: instantiated above
        async with self._driver.session() as session:
            yield session

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None


class QdrantVectorStoreManager:
    """Manage Qdrant connectivity, replication, and persistence policies."""

    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None  # type: ignore[assignment]
        self._lock = RLock()

    def _ensure_client(self) -> QdrantClient:  # type: ignore[override]
        if QdrantClient is None:  # pragma: no cover - environment without qdrant-client installed
            raise RuntimeError("Qdrant client requested but 'qdrant-client' dependency is missing")
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is not None:
                return self._client
            cfg = get_settings().qdrant
            kwargs = {
                "host": cfg.host,
                "port": cfg.port,
            }
            if cfg.grpc_port is not None:
                kwargs["grpc_port"] = cfg.grpc_port
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            if cfg.prefer_grpc:
                kwargs["prefer_grpc"] = True
            if cfg.tls_enabled:
                kwargs["https"] = True
            self._client = QdrantClient(**kwargs)
            return self._client

    @staticmethod
    def _distance(metric: str):
        if qdrant_models is None:  # pragma: no cover - defensive when qdrant-client absent
            raise RuntimeError("Qdrant models module unavailable")
        try:
            return getattr(qdrant_models.Distance, metric.upper())
        except AttributeError as exc:  # pragma: no cover - surfaced during bootstrap
            raise ConfigurationError(f"Unsupported Qdrant distance metric '{metric}'") from exc

    def ensure_collections(self) -> Sequence[str]:
        client = self._ensure_client()
        cfg = get_settings().qdrant
        ensured: List[str] = []

        if qdrant_models is None:
            raise RuntimeError("Qdrant models unavailable; cannot provision collections")

        for collection in cfg.collections:
            vectors_config = qdrant_models.VectorParams(
                size=collection.vector_size,
                distance=self._distance(collection.distance),
                on_disk_payload=collection.on_disk_payload,
            )

            try:
                client.get_collection(collection.name)
            except UnexpectedResponse:
                client.create_collection(
                    collection_name=collection.name,
                    vectors_config=vectors_config,
                    replication_factor=cfg.replication_factor,
                    write_consistency_factor=cfg.write_consistency_factor,
                    shard_number=collection.shard_number,
                    on_disk_payload=collection.on_disk_payload,
                )
            else:
                client.update_collection(
                    collection_name=collection.name,
                    replication_factor=cfg.replication_factor,
                    write_consistency_factor=cfg.write_consistency_factor,
                )

            ensured.append(collection.name)

        return ensured

    def planned_backup_jobs(self) -> Sequence[dict[str, str]]:
        cfg = get_settings().qdrant
        plans: List[dict[str, str]] = []
        if cfg.snapshot_schedule_cron:
            plans.append(
                {
                    "type": "snapshot",
                    "schedule": cfg.snapshot_schedule_cron,
                    "description": "Create Qdrant collection snapshots",
                }
            )
        if cfg.backup_schedule_cron and cfg.backup_storage_uri:
            plans.append(
                {
                    "type": "backup",
                    "schedule": cfg.backup_schedule_cron,
                    "destination": cfg.backup_storage_uri,
                    "description": "Ship Qdrant snapshots to durable storage",
                }
            )
        return plans

    def client(self) -> QdrantClient:  # type: ignore[override]
        return self._ensure_client()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


postgres_pool = PostgresPool()
redis_pool = RedisPool()
neo4j_driver = Neo4jDriver()
qdrant_manager = QdrantVectorStoreManager()


__all__ = [
    "PostgresPool",
    "RedisPool",
    "Neo4jDriver",
    "QdrantVectorStoreManager",
    "postgres_pool",
    "redis_pool",
    "neo4j_driver",
    "qdrant_manager",
]

