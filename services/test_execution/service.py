from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import random
import time

from services.test_generation.service import GeneratedTestCase


@dataclass
class ExecutedTestCase:
    name: str
    status: str
    duration_seconds: float
    log_excerpt: str


class TestExecutionService:
    """Simulated test execution runner."""

    def run(self, test_cases: List[GeneratedTestCase]) -> Dict[str, List[ExecutedTestCase]]:
        executed: List[ExecutedTestCase] = []
        random.seed(42)  # deterministic runs for the POC

        for case in test_cases:
            start_time = time.monotonic()
            simulated_duration = 0.1 + random.random() * 0.4
            time.sleep(0.01)  # tiny delay to mimic work without slowing down too much
            status = self._determine_status(case)
            log_excerpt = self._build_log(case, status)
            end_time = start_time + simulated_duration

            executed.append(
                ExecutedTestCase(
                    name=case.name,
                    status=status,
                    duration_seconds=round(end_time - start_time, 2),
                    log_excerpt=log_excerpt,
                )
            )

        return {"executed_tests": executed}

    def _determine_status(self, case: GeneratedTestCase) -> str:
        if case.priority == "P0":
            return random.choice(["failed", "passed", "failed"])
        if case.priority == "P1":
            return random.choice(["passed", "passed", "failed"])
        return "passed"

    def _build_log(self, case: GeneratedTestCase, status: str) -> str:
        if status == "passed":
            return f"{case.name} completed successfully."
        return (
            f"{case.name} failed on assertion. Suggested assertions were: "
            f"{'; '.join(case.suggested_assertions)}"
        )
