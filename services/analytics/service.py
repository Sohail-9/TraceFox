from __future__ import annotations

from typing import Dict, List

from services.common.models import AnalyticsReport, AnomalyAlert, RootCauseAnalysis, TestExecutionResult


class AnalyticsService:
    """Computes derived analytics from pipeline outputs."""

    def build_report(
        self,
        commit_id: str,
        tests: List[TestExecutionResult],
        rca_items: List[RootCauseAnalysis],
        alerts: List[AnomalyAlert],
    ) -> AnalyticsReport:
        failed = [test for test in tests if test.status == "failed"]
        insights: List[str] = []
        if failed:
            insights.append(
                f"{len(failed)} tests failed; prioritise RCA "
                f"with {', '.join(test.name for test in failed[:3])}."
            )
        if rca_items:
            insights.append(
                f"RCA generated for {len(rca_items)} failing tests; review suggestions before merging."
            )
        if alerts:
            insights.append(
                f"Deployment anomalies detected for "
                f"{', '.join(alert.metric for alert in alerts)}; verify rollback plans."
            )
        if not insights:
            insights.append("All signals nominal. Continue rollout.")

        return AnalyticsReport(
            commit_id=commit_id,
            tests_generated=len(tests),
            tests_failed=len(failed),
            notifications_sent=1,
            anomalies_detected=len(alerts),
            insights=insights,
        )
