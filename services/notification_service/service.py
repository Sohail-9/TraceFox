from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from services.debugging_service.service import RootCauseAnalysis
from services.test_execution.service import ExecutedTestCase


@dataclass
class NotificationMessage:
    channel: str
    body: str


class NotificationService:
    """Formats summary notifications for the POC."""

    def build_summary(
        self,
        commit_id: str,
        executed_tests: List[ExecutedTestCase],
        rca_items: List[RootCauseAnalysis],
    ) -> Dict[str, NotificationMessage]:
        failing_tests = [test for test in executed_tests if test.status == "failed"]
        severity = "high" if failing_tests else "info"

        body_lines: List[str] = [
            f"TraceFox summary for commit {commit_id}",
            f"Severity: {severity.upper()}",
            f"Tests executed: {len(executed_tests)} | Failures: {len(failing_tests)}",
        ]

        for rca in rca_items:
            line = f"- {rca.failing_test}: {rca.explanation}"
            if rca.similar_incident:
                line += f" Similar incident: {rca.similar_incident}."
            body_lines.append(line)

        if not rca_items:
            body_lines.append("All generated tests passed. No RCA required.")

        return {
            "slack": NotificationMessage(
                channel="#tracefox-demo", body="\n".join(body_lines)
            )
        }
