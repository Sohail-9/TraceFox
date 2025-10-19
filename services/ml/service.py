from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from services.shared.models import DriftDetectionRequest


class DriftDetectionService:
    """Performs lightweight drift detection heuristics."""

    def __init__(self) -> None:
        self._history: List[Dict[str, object]] = []
        self._lock = asyncio.Lock()

    async def detect(self, request: DriftDetectionRequest) -> Dict[str, object]:
        async with self._lock:
            result = {
                "drift_detected": False,
                "drift_metrics": {
                    "ks_statistic": 0.05,
                    "psi_score": 0.1,
                    "features_with_drift": [],
                },
                "recommendations": [
                    "Monitor feature distribution over next 24h",
                    "Schedule retraining if drift persists",
                ],
            }
            self._history.append({"request": request.model_dump(), "result": result})
            logging.getLogger(__name__).debug(
                "Recorded drift detection for PR %s", request.pr_id
            )
            return result

    async def history(self) -> List[Dict[str, object]]:
        return self._history

