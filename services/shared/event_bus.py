"""RabbitMQ-backed messaging abstraction using the management HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Dict, Optional
from urllib.parse import quote, urlparse

import httpx

from services.shared.config import get_settings

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """Durable pub/sub implemented via RabbitMQ management HTTP API."""

    def __init__(self) -> None:
        settings = get_settings().messaging
        parsed = urlparse(settings.broker_url)
        self._username = parsed.username or "guest"
        self._password = parsed.password or "guest"
        self._host = parsed.hostname or "localhost"
        self._vhost = parsed.path.lstrip("/") or "/"
        self._encoded_vhost = quote(self._vhost, safe="")
        self._exchange = "tracefox.events"
        self._delivery_timeout = settings.delivery_timeout_seconds
        management_base = settings.management_url or f"http://{self._host}:15672/api"
        self._management_base = management_base.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._poll_interval = 1.0
        self._consumer_tasks: Dict[str, asyncio.Task[None]] = {}

    async def _client_session(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            self._client = httpx.AsyncClient(
                auth=(self._username, self._password),
                timeout=15.0,
            )
            await self._declare_exchange()
            return self._client

    async def _declare_exchange(self) -> None:
        client = self._client
        if client is None:
            client = httpx.AsyncClient(
                auth=(self._username, self._password),
                timeout=15.0,
            )
            self._client = client
        url = f"{self._management_base}/exchanges/{self._encoded_vhost}/{quote(self._exchange, safe='')}"
        await client.put(
            url,
            json={"type": "topic", "durable": True, "auto_delete": False, "internal": False},
        )

    async def publish(self, topic: str, payload: dict) -> None:
        client = await self._client_session()
        url = f"{self._management_base}/exchanges/{self._encoded_vhost}/{quote(self._exchange, safe='')}/publish"
        await client.post(
            url,
            json={
                "routing_key": topic,
                "payload": json.dumps(payload),
                "payload_encoding": "string",
                "headers": {"x-tracefox-topic": topic},
                "props": {"expiration": str(int(self._delivery_timeout * 1000))},
            },
        )

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        client = await self._client_session()
        queue_name = f"tracefox.{topic.replace(':', '.')}"
        await self._declare_queue(queue_name)
        await self._bind_queue(queue_name, topic)
        task = asyncio.create_task(self._poll_queue(queue_name, topic, handler, client))
        self._consumer_tasks[queue_name] = task

    async def _declare_queue(self, queue_name: str) -> None:
        client = await self._client_session()
        url = f"{self._management_base}/queues/{self._encoded_vhost}/{quote(queue_name, safe='')}"
        await client.put(
            url,
            json={"durable": True, "arguments": {"x-expires": 600000}},
        )

    async def _bind_queue(self, queue_name: str, topic: str) -> None:
        client = await self._client_session()
        url = (
            f"{self._management_base}/bindings/{self._encoded_vhost}/e/"
            f"{quote(self._exchange, safe='')}/q/{quote(queue_name, safe='')}"
        )
        await client.post(url, json={"routing_key": topic})

    async def _poll_queue(
        self,
        queue_name: str,
        topic: str,
        handler: EventHandler,
        client: httpx.AsyncClient,
    ) -> None:
        get_url = f"{self._management_base}/queues/{self._encoded_vhost}/{quote(queue_name, safe='')}/get"
        payload = {
            "count": 20,
            "ackmode": "ack_requeue_false",
            "encoding": "auto",
            "truncate": 50000,
        }
        while True:
            try:
                response = await client.post(get_url, json=payload)
                response.raise_for_status()
                messages = response.json()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Polling queue %s failed: %s", queue_name, exc)
                await asyncio.sleep(self._poll_interval)
                continue
            if not messages:
                await asyncio.sleep(self._poll_interval)
                continue
            for entry in messages:
                body = entry.get("payload")
                if not body:
                    continue
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    logger.warning("Dropping malformed payload on %s", topic)
                    continue
                await handler(data)

    async def close(self) -> None:
        for task in self._consumer_tasks.values():
            task.cancel()
        self._consumer_tasks.clear()
        if self._client is not None:
            await self._client.aclose()
            self._client = None


event_bus = EventBus()
