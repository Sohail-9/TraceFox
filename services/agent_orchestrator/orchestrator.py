from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from services.analytics.service import AnalyticsService
from services.code_analysis.service import CodeAnalysisService, build_file_changes
from services.common.models import (
    AnalyticsReport,
    CommitEvent,
    DeploymentEvent,
    TestExecutionResult,
)
from services.debugging_service.service import DebuggingService
from services.knowledge_base.service import KnowledgeBaseService
from services.notification_service.service import NotificationService
from services.production_monitor.service import ProductionMonitorService
from services.test_execution.service import TestExecutionService
from services.test_generation.service import TestGenerationService
from services.user_management.service import UserManagementService


class DevGuardianOrchestrator:
    """Coordinates the DevGuardian workflow across development and production."""

    def __init__(self) -> None:
        self.code_analysis = CodeAnalysisService()
        self.test_generation = TestGenerationService()
        self.test_execution = TestExecutionService()
        self.knowledge_base = KnowledgeBaseService()
        self.debugging = DebuggingService(self.knowledge_base)
        self.notification = NotificationService()
        self.user_management = UserManagementService()
        self.production_monitor = ProductionMonitorService()
        self.analytics = AnalyticsService()
        self._latest_report: AnalyticsReport | None = None
        self._last_tests: List[TestExecutionResult] = []
        self._last_commit_payload: Dict[str, Any] | None = None
        self._last_deployment_payload: Dict[str, Any] | None = None

    def run_pipeline(self, commit_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_changes = build_file_changes(files)
        analysis_payload = self.code_analysis.analyze(file_changes)
        analyses = analysis_payload["files"]

        generated_tests_payload = self.test_generation.generate(analyses, commit_id)
        generated_tests = generated_tests_payload["tests"]

        execution_payload = self.test_execution.run(generated_tests)
        executed_tests = execution_payload["executed_tests"]
        self._last_tests = executed_tests

        rca_payload = self.debugging.run(executed_tests)
        rca_items = rca_payload["rca"]

        notification_payload = self.notification.build_summary(
            commit_id=commit_id,
            executed_tests=executed_tests,
            rca_items=rca_items,
            deployment_alerts=[],
        )

        analytics_report = self.analytics.build_report(
            commit_id=commit_id, tests=executed_tests, rca_items=rca_items, alerts=[]
        )
        self._latest_report = analytics_report

        result = {
            "code_analysis": {
                "files": [self._serialize_dataclass(item) for item in analyses],
                "summary": self._serialize_dataclass(analysis_payload["summary"]),
                "cache": analysis_payload["cache"],
            },
            "test_generation": {
                "tests": [self._serialize_dataclass(item) for item in generated_tests]
            },
            "test_execution": {
                "executed_tests": [
                    self._serialize_dataclass(item) for item in executed_tests
                ]
            },
            "debugging": {
                "rca": [self._serialize_dataclass(item) for item in rca_items],
            },
            "notification": {
                channel: self._serialize_dataclass(message)
                for channel, message in notification_payload.items()
            },
            "analytics": self._serialize_dataclass(analytics_report),
        }
        return result

    def process_commit(self, event: CommitEvent) -> Dict[str, Any]:
        context = self.user_management.get_user_context(event.author)
        payload = self.run_pipeline(
            commit_id=event.commit_id,
            files=[asdict(file) for file in event.files],
        )
        payload["user_context"] = asdict(context)
        payload["event"] = {
            "repository": event.repository,
            "branch": event.branch,
            "timestamp": event.timestamp.isoformat(),
        }
        self._last_commit_payload = payload
        return payload

    def process_deployment(
        self, event: DeploymentEvent, metrics: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        alerts = self.production_monitor.analyse_metrics(metrics)
        notifications = self.notification.build_summary(
            commit_id=event.commit_id,
            executed_tests=[],
            rca_items=[],
            deployment_alerts=[
                f"{alert.metric} deviated (observed {alert.observed}, baseline {alert.baseline})"
                for alert in alerts
            ],
        )

        analytics_report = self.analytics.build_report(
            commit_id=event.commit_id,
            tests=self._last_tests,
            rca_items=[],
            alerts=alerts,
        )
        self._latest_report = analytics_report

        payload = {
            "deployment": {
                "deployment_id": event.deployment_id,
                "commit_id": event.commit_id,
                "environment": event.environment,
                "timestamp": event.timestamp.isoformat(),
            },
            "alerts": [self._serialize_dataclass(alert) for alert in alerts],
            "notification": {
                channel: self._serialize_dataclass(message)
                for channel, message in notifications.items()
            },
            "analytics": self._serialize_dataclass(analytics_report),
        }
        self._last_deployment_payload = payload
        return payload

    def latest_report(self) -> Dict[str, Any] | None:
        if not self._latest_report:
            return None
        return self._serialize_dataclass(self._latest_report)

    def current_state(self) -> Dict[str, Any]:
        return {
            "latest_report": self.latest_report(),
            "last_commit": self._last_commit_payload,
            "last_deployment": self._last_deployment_payload,
        }

    def _serialize_dataclass(self, item: Any) -> Dict[str, Any]:
        return asdict(item)
