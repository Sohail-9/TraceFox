from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from services.shared.event_bus import event_bus
from services.shared.models import TestCase, TestExecutionRequest, TestExecutionResult


class TestExecutionService:
    """Coordinates containerised test execution with simulated results."""

    def __init__(self) -> None:
        self._executions: Dict[str, Dict[str, object]] = {}
        self._lock = asyncio.Lock()

    async def execute(
        self, request: TestExecutionRequest, tests: List[TestCase]
    ) -> Dict[str, object]:
        async with self._lock:
            execution_id = str(uuid4())
            results = [self._run_single_test(test) for test in tests]
            summary = self._summarise_results(results)
            completed_at = datetime.utcnow().isoformat() + "Z"
            payload = {
                "execution_id": execution_id,
                "pr_id": request.pr_id,
                "test_case_ids": request.test_case_ids,
                "results": results,
                "total_tests": len(results),
                "completed_at": completed_at,
                **summary,
            }
            self._executions[execution_id] = payload
            await event_bus.publish("tests:executed", payload)
            logging.getLogger(__name__).info(
                "Executed %s tests for PR %s", len(results), request.pr_id
            )
            return {
                "execution_id": execution_id,
                "status": "completed",
                "total_tests": len(results),
                "passed": summary["passed"],
                "failed": summary["failed"],
                "flaky": summary["flaky"],
                "skipped": summary["skipped"],
                "execution_time_ms": summary["execution_time_ms"],
                "completed_at": completed_at,
            }

    async def get_execution(self, execution_id: str) -> Optional[Dict[str, object]]:
        return self._executions.get(execution_id)

    def _run_single_test(self, test: TestCase) -> Dict[str, object]:
        status = random.choices(
            population=["passed", "failed", "flaky"],
            weights=[0.7, 0.2, 0.1],
        )[0]
        execution_time = random.randint(10, 120) * 1000
        error_message = None if status == "passed" else "AssertionError: simulated failure"
        stack_trace = (
            "Traceback (most recent call last):\n  File \"tests/test_sample.py\", line 10, in test_case"
            if status == "failed"
            else None
        )
        return TestExecutionResult(
            execution_id=str(uuid4()),
            test_case_id=test.id,
            test_name=test.test_name,
            status=status,
            execution_time_ms=execution_time,
            error_message=error_message,
            stack_trace=stack_trace,
        ).model_dump()

    def _summarise_results(self, results: List[Dict[str, object]]) -> Dict[str, int]:
        summary = {"passed": 0, "failed": 0, "flaky": 0, "skipped": 0}
        total_time = 0
        for result in results:
            summary[result["status"]] += 1  # type: ignore[index]
            total_time += result["execution_time_ms"]  # type: ignore[operator]
        summary["execution_time_ms"] = total_time
        return summary
