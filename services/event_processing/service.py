from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from services.agent_orchestrator.orchestrator import DevGuardianOrchestrator
from services.common.models import CommitEvent, DeploymentEvent, FileChange


class EventProcessingService:
    """Simplified event bus that forwards events to the orchestrator."""

    def __init__(self, orchestrator: DevGuardianOrchestrator) -> None:
        self.orchestrator = orchestrator

    def handle_commit_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        files = [
            FileChange(
                path=item["path"],
                content=item["content"],
                language=item.get("language", "python"),
            )
            for item in payload.get("files", [])
        ]
        timestamp = self._resolve_timestamp(payload.get("timestamp"))
        event = CommitEvent(
            commit_id=payload["commit_id"],
            repository=payload.get("repository", "devguardian/demo"),
            author=payload.get("author", "unknown"),
            timestamp=timestamp,
            files=files,
            branch=payload.get("branch", "main"),
        )
        return self.orchestrator.process_commit(event)

    def handle_deployment_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = self._resolve_timestamp(payload.get("timestamp"))
        event = DeploymentEvent(
            deployment_id=payload["deployment_id"],
            commit_id=payload["commit_id"],
            environment=payload.get("environment", "production"),
            timestamp=timestamp,
        )
        metrics = [
            {"name": metric["name"], "value": metric["value"], "unit": metric.get("unit", "")}
            for metric in payload.get("metrics", [])
        ]
        return self.orchestrator.process_deployment(event, metrics)

    def _resolve_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return datetime.utcnow()
