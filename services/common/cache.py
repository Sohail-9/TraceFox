from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class CacheEntry:
    key: Tuple[Any, ...]
    value: Any
    hit_count: int = 0


class ResponseCache:
    """Tiny in-memory cache to demonstrate DevGuardian response caching."""

    def __init__(self) -> None:
        self._items: Dict[Tuple[Any, ...], CacheEntry] = {}

    def get(self, *key_parts: Any) -> Optional[Any]:
        key = tuple(key_parts)
        entry = self._items.get(key)
        if not entry:
            return None
        entry.hit_count += 1
        return entry.value

    def set(self, value: Any, *key_parts: Any) -> None:
        key = tuple(key_parts)
        self._items[key] = CacheEntry(key=key, value=value)

    def stats(self) -> Dict[str, int]:
        hits = sum(entry.hit_count for entry in self._items.values())
        return {"keys": len(self._items), "hits": hits}
