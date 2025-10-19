"""Cache helpers enforcing versioned keys and configuration-driven TTLs."""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from services.shared.config import get_settings
from services.shared.database import redis_pool


class CacheKeyBuilder:
    """Build cache keys with namespace and version prefixes."""

    def __init__(self) -> None:
        cfg = get_settings().cache
        self._namespace = cfg.namespace
        self._version = cfg.version

    def compose(self, parts: Sequence[str]) -> str:
        suffix = ":".join(parts)
        return f"{self._namespace}:{self._version}:{suffix}"


class CacheClient:
    """High-level cache operations with deterministic versioning."""

    def __init__(self) -> None:
        self._builder: Optional[CacheKeyBuilder] = None

    async def set_json(self, key_parts: Sequence[str], payload: Any, *, ttl: Optional[int] = None) -> None:
        client = await redis_pool.connect()
        builder = self._builder or CacheKeyBuilder()
        self._builder = builder
        effective_ttl = ttl if ttl is not None else get_settings().cache.default_ttl_seconds
        key = builder.compose(key_parts)
        await client.set(key, json.dumps(payload).encode("utf-8"), ex=effective_ttl)

    async def get_json(self, key_parts: Sequence[str]) -> Optional[Any]:
        client = await redis_pool.connect()
        builder = self._builder or CacheKeyBuilder()
        self._builder = builder
        key = builder.compose(key_parts)
        payload = await client.get(key)
        if payload is None:
            return None
        return json.loads(payload)

    async def delete(self, key_parts: Sequence[str]) -> None:
        client = await redis_pool.connect()
        builder = self._builder or CacheKeyBuilder()
        self._builder = builder
        key = builder.compose(key_parts)
        await client.delete(key)


cache = CacheClient()


__all__ = [
    "cache",
    "CacheClient",
]
