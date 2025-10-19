from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List


class ObservabilityService:
    """Stores in-memory metrics for latency, errors, and health thresholds."""

    def __init__(self) -> None:
        self._metrics: DefaultDict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def record_metric(self, name: str, value: float) -> None:
        async with self._lock:
            self._metrics[name].append(value)
            logging.getLogger(__name__).debug("Recorded metric %s=%s", name, value)

    async def summary(self) -> Dict[str, Dict[str, float]]:
        summary: Dict[str, Dict[str, float]] = {}
        for name, values in self._metrics.items():
            if not values:
                continue
            summary[name] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
            }
        return summary

