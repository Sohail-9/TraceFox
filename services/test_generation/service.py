from __future__ import annotations

import asyncio
import logging
import random
from typing import Dict, List
from uuid import uuid4

from services.shared.models import (
    FindingCategory,
    ReviewFinding,
    ReviewSummary,
    Severity,
    TestCase,
    TestGenerationRequestPayload,
    TestType,
)


class TestGenerationService:
    """Generates targeted tests based on AI review findings and code graph context."""

    def __init__(self) -> None:
        self._tests: Dict[str, List[TestCase]] = {}
        self._lock = asyncio.Lock()

    async def generate_tests(
        self,
        request: TestGenerationRequestPayload,
        review: ReviewSummary | None,
    ) -> Dict[str, List[TestCase]]:
        async with self._lock:
            findings = self._select_findings(request, review)
            generated: List[TestCase] = []
            for finding in findings:
                for test_type in request.test_types:
                    generated.append(self._build_test_case(request.pr_id, finding, test_type))

            self._tests.setdefault(request.pr_id, [])
            self._tests[request.pr_id].extend(generated)
            logging.getLogger(__name__).info(
                "Generated %s tests for PR %s", len(generated), request.pr_id
            )
            return {"tests": generated, "total_generated": len(generated)}

    async def list_tests(self, pr_id: str) -> List[TestCase]:
        return self._tests.get(pr_id, [])

    def _select_findings(
        self, request: TestGenerationRequestPayload, review: ReviewSummary | None
    ) -> List[ReviewFinding]:
        if not review:
            placeholder = ReviewFinding(
                id=str(uuid4()),
                file_path="unknown.py",
                line_number=1,
                severity=random.choice(list(Severity)),
                category=random.choice(list(FindingCategory)),
                description="Placeholder finding due to missing review.",
                suggested_fix=None,
                confidence_score=0.5,
            )
            return [placeholder]
        if not request.finding_ids:
            return review.findings
        return [f for f in review.findings if f.id in request.finding_ids]

    def _build_test_case(
        self, pr_id: str, finding: ReviewFinding, test_type: TestType
    ) -> TestCase:
        test_id = str(uuid4())
        return TestCase(
            id=test_id,
            pull_request_id=pr_id,
            finding_id=finding.id,
            test_name=f"{test_type.value}_test_{finding.file_path.replace('/', '_')}",
            test_type=test_type,
            test_code=self._generate_test_code(finding, test_type),
            priority=self._priority_from_severity(finding.severity),
            root_cause_mapping=f"Finding {finding.id}",
            language="python",
            framework="pytest",
        )

    def _generate_test_code(self, finding: ReviewFinding, test_type: TestType) -> str:
        return (
            f"def test_{finding.id[:8]}_{test_type.value.replace('-', '_')}():\n"
            f"    # TODO: auto-generated test skeleton for {finding.file_path}\n"
            f"    assert True\n"
        )

    def _priority_from_severity(self, severity: Severity) -> int:
        mapping = {
            Severity.critical: 1,
            Severity.major: 2,
            Severity.minor: 3,
        }
        return mapping.get(severity, 4)
