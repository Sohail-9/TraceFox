from __future__ import annotations

from typing import Dict, List

from services.common.model_router import ModelRouter
from services.common.models import RootCauseAnalysis, TestExecutionResult
from services.knowledge_base.service import KnowledgeBaseService


class DebuggingService:
    """Simplified debugging workflow that mimics DevGuardian's RCA."""

    def __init__(self, knowledge_base: KnowledgeBaseService) -> None:
        self.knowledge_base = knowledge_base
        self._router = ModelRouter()

    def run(
        self, executed_tests: List[TestExecutionResult], locale: str = "en"
    ) -> Dict[str, List[RootCauseAnalysis]]:
        analyses: List[RootCauseAnalysis] = []

        for test in executed_tests:
            if test.status != "failed":
                continue

            model = self._router.select_for_rca(
                severity="high" if test.retry_required else "medium", locale=locale
            )
            similar = self.knowledge_base.lookup_by_keywords(test.log_excerpt)

            analyses.append(
                RootCauseAnalysis(
                    failing_test=test.name,
                    explanation=self._build_explanation(test),
                    suggested_fix=self._suggest_fix(test),
                    similar_incident=similar,
                    confidence=0.65 if similar else 0.5,
                    model_selected=model,
                )
            )

        return {"rca": analyses}

    def _build_explanation(self, test: TestExecutionResult) -> str:
        return (
            f"Test {test.name} failed during simulated execution. "
            f"DevGuardian suspects a regression introduced in the recent commit."
        )

    def _suggest_fix(self, test: TestExecutionResult) -> str:
        return (
            "Inspect the assertions referenced in the generated test and align the "
            "implementation with the updated requirements."
        )
