from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Any

from services.code_analysis.service import (
    CodeAnalysisService,
    FileAnalysis,
    build_file_changes,
)
from services.debugging_service.service import DebuggingService
from services.knowledge_base.service import KnowledgeBaseService
from services.notification_service.service import NotificationService
from services.test_execution.service import TestExecutionService
from services.test_generation.service import TestGenerationService


class TraceFoxOrchestrator:
    """Coordinates the simulated TraceFox workflow for the MVP."""

    def __init__(self) -> None:
        self.code_analysis = CodeAnalysisService()
        self.test_generation = TestGenerationService()
        self.test_execution = TestExecutionService()
        self.knowledge_base = KnowledgeBaseService()
        self.debugging = DebuggingService(self.knowledge_base)
        self.notification = NotificationService()

    def run_pipeline(self, commit_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_changes = build_file_changes(files)
        analysis_payload = self.code_analysis.analyze(file_changes)
        analyses = analysis_payload["files"]

        generated_tests_payload = self.test_generation.generate(analyses, commit_id)
        generated_tests = generated_tests_payload["tests"]

        execution_payload = self.test_execution.run(generated_tests)
        executed_tests = execution_payload["executed_tests"]

        rca_payload = self.debugging.run(executed_tests)
        rca_items = rca_payload["rca"]

        notification_payload = self.notification.build_summary(
            commit_id=commit_id, executed_tests=executed_tests, rca_items=rca_items
        )

        return {
            "code_analysis": {
                "files": [self._serialize_dataclass(item) for item in analyses],
                "summary": analysis_payload["summary"],
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
        }

    def _serialize_dataclass(self, item: Any) -> Dict[str, Any]:
        return asdict(item)
