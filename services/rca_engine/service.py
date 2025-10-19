from __future__ import annotations

import asyncio
import logging
import random
from typing import Dict, List, Optional
from uuid import uuid4

from services.shared.event_bus import event_bus
from services.shared.models import RCACategory, RCAFinding


class RCAEngine:
    """Performs simulated RCA using commit correlation and historical patterns."""

    def __init__(self) -> None:
        self._rca_results: Dict[str, RCAFinding] = {}
        self._lock = asyncio.Lock()

    async def analyse(self, execution_id: str, failed_tests: List[Dict[str, object]]) -> Optional[RCAFinding]:
        if not failed_tests:
            return None
        async with self._lock:
            failure = random.choice(failed_tests)
            finding = RCAFinding(
                id=str(uuid4()),
                test_execution_id=execution_id,
                category=random.choice(list(RCACategory)),
                root_cause_summary="Identified potential concurrency issue.",
                root_cause_details={
                    "failure_test": failure.get("test_name"),
                    "stack_trace": failure.get("stack_trace"),
                },
                correlated_commits=[
                    {
                        "commit_hash": "abc123def456",
                        "author": "tracefox",
                        "message": "Simulated commit correlation",
                        "timestamp": "2025-01-01T00:00:00Z",
                        "correlation_score": round(random.uniform(0.7, 0.95), 2),
                        "changed_files": ["src/services/example.py"],
                    }
                ],
                suggested_fixes=[
                    {
                        "file_path": "src/services/example.py",
                        "fix_description": "Introduce transaction isolation.",
                        "code_diff": "+ # TODO: Apply fix\n",
                    }
                ],
                confidence_score=round(random.uniform(0.6, 0.9), 2),
                prevention_recommendations=[
                    "Add integration tests for concurrent paths",
                    "Implement retry with backoff",
                ],
            )
            self._rca_results[execution_id] = finding
            await event_bus.publish(
                "rca:completed",
                {"execution_id": execution_id, "rca_id": finding.id, "category": finding.category.value},
            )
            logging.getLogger(__name__).info(
                "Generated RCA %s for execution %s", finding.id, execution_id
            )
            return finding

    async def get_rca(self, execution_id: str) -> Optional[RCAFinding]:
        return self._rca_results.get(execution_id)

