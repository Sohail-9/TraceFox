from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from services.shared.models import ComplianceReport, ComplianceRequirement


@dataclass
class ComplianceSnapshot:
    report: ComplianceReport


class ComplianceService:
    """Maintains compliance coverage snapshots by standard."""

    def __init__(self) -> None:
        self._reports: Dict[str, ComplianceSnapshot] = {}
        self._lock = asyncio.Lock()

    async def store_report(self, standard: str, repository_id: str, report: ComplianceReport) -> None:
        key = self._key(standard, repository_id)
        async with self._lock:
            self._reports[key] = ComplianceSnapshot(report=report)
            logging.getLogger(__name__).info("Stored compliance report %s", key)

    async def get_report(self, standard: str, repository_id: str) -> Optional[ComplianceReport]:
        key = self._key(standard, repository_id)
        snapshot = self._reports.get(key)
        return snapshot.report if snapshot else None

    async def seed_default_report(self, standard: str, repository_id: str) -> ComplianceReport:
        requirements = [
            ComplianceRequirement(
                requirement_id="placeholder-1",
                description="Simulated requirement coverage.",
                status="covered",
                test_cases=["test_sql_injection_prevention"],
            ),
            ComplianceRequirement(
                requirement_id="placeholder-2",
                description="Pending coverage item.",
                status="missing",
                test_cases=[],
                recommendation="Add network segmentation tests.",
            ),
        ]
        report = ComplianceReport(
            standard=standard,
            total_requirements=len(requirements),
            covered_requirements=sum(1 for req in requirements if req.status == "covered"),
            coverage_percentage=round(
                sum(1 for req in requirements if req.status == "covered") / len(requirements) * 100, 2
            ),
            requirements=requirements,
        )
        await self.store_report(standard, repository_id, report)
        return report

    def _key(self, standard: str, repository_id: str) -> str:
        return f"{standard}:{repository_id}"

