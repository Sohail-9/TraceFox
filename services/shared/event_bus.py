"""Internal messaging abstraction for service-to-service communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, Dict, List

from services.shared.config import ConfigurationError, get_settings

EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """Simple in-memory async pub/sub bus with backpressure awareness."""

    def __init__(self) -> None:
        self._topics: Dict[str, asyncio.Queue[dict]] = defaultdict(self._build_queue)
        self._consumer_tasks: Dict[str, List[asyncio.Task[None]]] = defaultdict(list)

    @staticmethod
    def _queue_size() -> int:
        try:
            return get_settings().messaging.queue_max_size
        except ConfigurationError as exc:  # pragma: no cover - surfaces during bootstrap
            raise RuntimeError("Messaging configuration is required before using the event bus") from exc

    def _build_queue(self) -> asyncio.Queue[dict]:
        return asyncio.Queue(maxsize=self._queue_size())

    async def publish(self, topic: str, payload: dict) -> None:
        queue = self._topics[topic]
        await queue.put(payload)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        queue = self._topics[topic]

        async def _consume() -> None:
            while True:
                message = await queue.get()
                try:
                    await handler(message)
                finally:
                    queue.task_done()

        task = asyncio.create_task(_consume(), name=f"event-consumer:{topic}")
        self._consumer_tasks[topic].append(task)

    async def close(self) -> None:
        for tasks in self._consumer_tasks.values():
            for task in tasks:
                task.cancel()

    @asynccontextmanager
    async def consumer_group(self, topic: str, handler: EventHandler) -> AsyncIterator:
        await self.subscribe(topic, handler)
        try:
            yield
        finally:
            await self.close()


event_bus = EventBus()

try:
    for group in get_settings().messaging.consumer_groups:
        event_bus._topics.setdefault(group, event_bus._build_queue())
except ConfigurationError:
    # Topics will be initialised lazily once configuration becomes available.
    pass
