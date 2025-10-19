"""Internal messaging abstraction for service-to-service communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, Dict, List

from services.shared.config import settings

EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """Simple in-memory async pub/sub bus with backpressure awareness."""

    def __init__(self) -> None:
        self._topics: Dict[str, asyncio.Queue[dict]] = defaultdict(
            lambda: asyncio.Queue(maxsize=1024)
        )
        self._consumer_tasks: Dict[str, List[asyncio.Task[None]]] = defaultdict(list)

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

# Pre-register known topics derived from messaging config
for group in settings.messaging.consumer_groups:
    event_bus._topics.setdefault(group, asyncio.Queue(maxsize=1024))

