from __future__ import annotations

import asyncio
import logging
import random
from typing import Dict, Optional
from uuid import uuid4

from services.shared.event_bus import event_bus
from services.shared.models import (
    FindingCategory,
    ReviewFinding,
    ReviewSummary,
    Severity,
    WebhookPayload,
)


class AIReviewEngine:
    """Coordinates AI models and static analysis to produce review findings."""

    def __init__(self) -> None:
        self._reviews: Dict[str, ReviewSummary] = {}
        self._lock = asyncio.Lock()

    async def run_review(self, pr_id: str, payload: WebhookPayload) -> ReviewSummary:
        async with self._lock:
            findings = [
                ReviewFinding(
                    id=str(uuid4()),
                    file_path=f"src/module_{idx}.py",
                    line_number=random.randint(1, 200),
                    severity=random.choice(list(Severity)),
                    category=random.choice(list(FindingCategory)),
                    description=f"Automated observation {idx}",
                    suggested_fix="Apply recommended fix template.",
                    confidence_score=round(random.uniform(0.6, 0.95), 2),
                )
                for idx in range(random.randint(1, 4))
            ]
            summary = ReviewSummary(
                review_id=str(uuid4()),
                pr_id=pr_id,
                summary=f"Found {len(findings)} issues via AI multi-model review.",
                findings=findings,
                total_findings=len(findings),
                critical_count=sum(1 for f in findings if f.severity == Severity.critical),
                major_count=sum(1 for f in findings if f.severity == Severity.major),
                minor_count=sum(1 for f in findings if f.severity == Severity.minor),
            )
            self._reviews[pr_id] = summary
            await event_bus.publish(
                "review:completed",
                {"pr_id": pr_id, "review_id": summary.review_id, "total_findings": len(findings)},
            )
            logging.getLogger(__name__).info(
                "Generated review %s for PR %s", summary.review_id, pr_id
            )
            return summary

    async def get_review(self, pr_id: str) -> Optional[ReviewSummary]:
        return self._reviews.get(pr_id)

