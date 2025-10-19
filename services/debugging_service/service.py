from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from services.knowledge_base.service import KnowledgeBaseService
from services.test_execution.service import ExecutedTestCase


@dataclass
class RootCauseAnalysis:
    failing_test: str
    explanation: str
    suggested_fix: str
    similar_incident: Optional[str]
    confidence: float


class DebuggingService:
    """Simplified debugging workflow that mimics TraceFox's RCA."""

    def __init__(self, knowledge_base: KnowledgeBaseService) -> None:
        self.knowledge_base = knowledge_base

    def run(self, executed_tests: List[ExecutedTestCase]) -> Dict[str, List[RootCauseAnalysis]]:
        analyses: List[RootCauseAnalysis] = []

        for test in executed_tests:
            if test.status != "failed":
                continue

            similar = self.knowledge_base.lookup_by_keywords(test.log_excerpt)

            analyses.append(
                RootCauseAnalysis(
                    failing_test=test.name,
                    explanation=self._build_explanation(test),
                    suggested_fix=self._suggest_fix(test),
                    similar_incident=similar,
                    confidence=0.65 if similar else 0.5,
                )
            )

        return {"rca": analyses}

    def _build_explanation(self, test: ExecutedTestCase) -> str:
        return (
            f"Test {test.name} failed during simulated execution. "
            f"TraceFox suspects a regression introduced in the recent commit."
        )

    def _suggest_fix(self, test: ExecutedTestCase) -> str:
        return (
            "Inspect the assertions referenced in the generated test and align the "
            "implementation with the updated requirements."
        )
