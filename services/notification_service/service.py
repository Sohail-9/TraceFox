from __future__ import annotations

from typing import Dict, List

from services.common.models import (
    NotificationMessage,
    RootCauseAnalysis,
    TestExecutionResult,
)

class NotificationService:
    """Formats summary notifications for DevGuardian channels."""

    def build_summary(
        self,
        commit_id: str,
        executed_tests: List[TestExecutionResult],
        rca_items: List[RootCauseAnalysis],
        deployment_alerts: List[str],
    ) -> Dict[str, NotificationMessage]:
        failing_tests = [test for test in executed_tests if test.status == "failed"]
        severity = "high" if failing_tests else "info"

        body_lines: List[str] = [
            f"DevGuardian summary for commit {commit_id}",
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

        if deployment_alerts:
            body_lines.append("Production alerts:")
            body_lines.extend(f"  • {alert}" for alert in deployment_alerts)

        return {
            "slack": NotificationMessage(
                channel="#devguardian-demo",
                body="\n".join(body_lines),
                severity=severity,
            ),
            "email": NotificationMessage(
                channel="alerts@devguardian.ai",
                body="\n".join(body_lines),
                severity=severity,
            )
        }
