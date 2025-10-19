"""Database connection pools and clients shared across services."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncSession
from redis.asyncio import Redis

try:
    import lancedb  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency in development
    lancedb = None

from services.shared.config import settings


class PostgresPool:
    """Asyncpg-based connection pool with lazy initialisation."""

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        if self._pool:
            return
        async with self._lock:
            if self._pool:
                return
            cfg = settings.postgres
            self._pool = await asyncpg.create_pool(
                host=cfg.host,
                port=cfg.port,
                user=cfg.user,
                password=cfg.password,
                database=cfg.database,
                min_size=cfg.min_pool,
                max_size=cfg.max_pool,
                timeout=30,
            )

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        if not self._pool:
            await self.init()
        assert self._pool is not None  # nosec: defensive
        async with self._pool.acquire() as conn:
            yield conn


class RedisPool:
    """Redis asyncio client with automatic reconnect."""

    def __init__(self) -> None:
        cfg = settings.redis
        password = cfg.password
        username = cfg.username
        self._client = Redis(
            host=cfg.host,
            port=cfg.port,
            username=username,
            password=password,
            db=cfg.db,
            max_connections=cfg.max_connections,
            socket_timeout=cfg.socket_timeout,
            decode_responses=False,
        )

    @property
    def client(self) -> Redis:
        return self._client


class Neo4jDriver:
    """Neo4j driver factory using async driver."""

    def __init__(self) -> None:
        cfg = settings.neo4j
        self._driver = AsyncGraphDatabase.driver(
            cfg.uri,
            auth=(cfg.user, cfg.password),
            max_connection_pool_size=cfg.max_connection_pool_size,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._driver.session() as session:
            yield session

    async def close(self) -> None:
        await self._driver.close()


class LanceDBClient:
    """LanceDB client wrapper providing lazy dataset creation."""

    def __init__(self, uri: Optional[str] = None) -> None:
        if lancedb is None:  # pragma: no cover
            raise RuntimeError(
                "LanceDB client requested but `lancedb` package is not installed."
            )
        self._client = lancedb.connect(uri) if uri else lancedb.connect()

    def table(self, name: str):
        if name not in self._client.table_names():
            self._client.create_table(name, data=[])
        return self._client.open_table(name)


postgres_pool = PostgresPool()
redis_pool = RedisPool()
neo4j_driver = Neo4jDriver()
