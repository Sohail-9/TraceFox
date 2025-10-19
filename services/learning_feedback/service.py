from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List

from services.shared.event_bus import event_bus
from services.shared.models import FeedbackPayload


class LearningFeedbackService:
    """Captures user feedback to improve model routing and scoring."""

    def __init__(self) -> None:
        self._feedback: DefaultDict[str, List[FeedbackPayload]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def record_feedback(self, payload: FeedbackPayload) -> Dict[str, str]:
        async with self._lock:
            self._feedback[payload.target_id].append(payload)
            await event_bus.publish("feedback:recorded", payload.model_dump())
            logging.getLogger(__name__).debug(
                "Recorded feedback for %s", payload.target_id
            )
            return {"status": "stored"}

    async def aggregate_scores(self, target_id: str) -> Dict[str, object]:
        feedback_list = self._feedback.get(target_id, [])
        total = len(feedback_list)
        thumbs_up = sum(1 for item in feedback_list if item.reaction == "thumbs_up")
        thumbs_down = sum(1 for item in feedback_list if item.reaction == "thumbs_down")
        return {
            "target_id": target_id,
            "total_feedback": total,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "approval_rate": thumbs_up / total if total else 0,
        }

