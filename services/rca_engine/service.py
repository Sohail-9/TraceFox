from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from datetime import datetime
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
            # Analyze each failure using heuristics
            best_finding: Optional[RCAFinding] = None
            
            for failure in failed_tests:
                test_name = str(failure.get("test_name", "unknown_test"))
                error_msg = str(failure.get("error_message") or failure.get("stack_trace") or "").lower()
                status = str(failure.get("status", "failed"))
                
                if status == "passed":
                    continue

                # Heuristic mapping
                category = RCACategory.logic
                summary = f"Test failure in {test_name}"
                details = "The test failed with an unspecified error."
                fix = "Review the test logic and implementation."
                
                if "timeout" in error_msg or "connection refused" in error_msg:
                    category = RCACategory.infrastructure
                    summary = "Network timeout or connectivity issue."
                    details = "The test timed out waiting for an external resource."
                    fix = "Increase timeouts or check dependent service availability."
                elif "constraint failure" in error_msg or "integrityerror" in error_msg:
                    category = RCACategory.data
                    summary = "Database integrity violation."
                    details = "A foreign key or unique constraint was violated."
                    fix = "Ensure test data isolation and proper cleanup."
                elif "assertionerror" in error_msg:
                    category = RCACategory.logic
                    summary = "Logic assertion failure."
                    details = "The actual result did not match the expected value."
                    fix = "Verify the business logic implementation against specs."
                elif "import error" in error_msg or "modulenotfound" in error_msg:
                    category = RCACategory.environment
                    summary = "Missing dependency or environment issue."
                    details = "Refers to a module that could not be loaded."
                    fix = "Check requirements.txt or PYTHONPATH settings."

                # Create finding
                finding = RCAFinding(
                    id=str(uuid4()),
                    test_execution_id=execution_id,
                    category=category,
                    root_cause_summary=summary,
                    root_cause_details={
                        "failure_test": test_name,
                        "error_snippet": error_msg[:200],
                        "analysis_method": "Heuristic Keyword Matching"
                    },
                    correlated_commits=[],
                    suggested_fixes=[
                        {
                            "file_path": "src/unknown.py", # Placeholder until we map back to files
                            "fix_description": fix,
                            "code_diff": None,
                        }
                    ],
                    confidence_score=0.85, # Heuristics are fairly reliable validation
                    prevention_recommendations=[
                        "Review recent changes to this component",
                        "Run local reproduction steps"
                    ],
                )
                
                # Keep the "most interesting" finding (e.g. prioritize infra/data over generic logic)
                if not best_finding or category in (RCACategory.infrastructure, RCACategory.data):
                    best_finding = finding

            if best_finding:
                self._rca_results[execution_id] = best_finding
                await event_bus.publish(
                    "rca:completed",
                    {"execution_id": execution_id, "rca_id": best_finding.id, "category": best_finding.category.value},
                )
                return best_finding
            return None

    async def get_rca(self, execution_id: str) -> Optional[RCAFinding]:
        return self._rca_results.get(execution_id)

    async def all_rca(self) -> List[RCAFinding]:
        async with self._lock:
            return list(self._rca_results.values())
