from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List
from uuid import uuid4

from services.shared.llm_utils import call_chat_completion
from services.shared.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    ReviewSummary,
    TestCase,
    TestGenerationRequestPayload,
    TestType,
)

logger = logging.getLogger(__name__)


class TestGenerationService:
    """Generates targeted tests based on AI review findings and code graph context."""

    def __init__(self) -> None:
        self._tests: Dict[str, List[TestCase]] = {}
        self._lock = asyncio.Lock()
        self._generation_model = "Gemma-3-27B-IT"

    async def generate_tests(
        self,
        request: TestGenerationRequestPayload,
        review: ReviewSummary | None,
    ) -> Dict[str, List[TestCase]]:
        async with self._lock:
            findings = self._select_findings(request, review)
            generated = await self._invoke_generation_model(request, findings)

            if not generated:
                generated = self._fallback_tests(request, findings)

            self._tests.setdefault(request.pr_id, [])
            self._tests[request.pr_id].extend(generated)
            logger.info("Generated %s tests for PR %s", len(generated), request.pr_id)
            return {"tests": generated, "total_generated": len(generated)}

    async def list_tests(self, pr_id: str) -> List[TestCase]:
        return self._tests.get(pr_id, [])

    def _select_findings(
        self, request: TestGenerationRequestPayload, review: ReviewSummary | None
    ) -> List[Finding]:
        if not review or not review.findings:
            placeholder = Finding(
                id=str(uuid4()),
                type=FindingCategory.logic,
                severity=FindingSeverity.low,
                confidence=0.2,
                message="TraceFox fallback finding: detailed review unavailable.",
                file_path="unknown.py",
                line_number=1,
                suggested_fix="Re-run review engine once analysis is ready.",
            )
            return [placeholder]
        if not request.finding_ids:
            return review.findings
        return [f for f in review.findings if f.id in request.finding_ids]

    async def _invoke_generation_model(
        self,
        request: TestGenerationRequestPayload,
        findings: List[Finding],
    ) -> List[TestCase]:
        if not findings:
            return []

        messages = self._build_generation_messages(request, findings)
        try:
            response = await asyncio.to_thread(
                call_chat_completion,
                self._generation_model,
                messages,
                stream=False,
                max_tokens=1536,
                temperature=0.35,
            )
            cases = self._parse_generation_response(request, response, findings)
            return cases
        except Exception as exc:  # pragma: no cover - LLM failures handled gracefully
            logger.error("Gemma test generation failed: %s", exc, exc_info=True)
            return []

    def _build_generation_messages(
        self, request: TestGenerationRequestPayload, findings: List[Finding]
    ) -> List[Dict[str, Any]]:
        findings_section = []
        for idx, finding in enumerate(findings, start=1):
            findings_section.append(
                json.dumps(
                    {
                        "id": finding.id,
                        "file_path": finding.file_path,
                        "line_number": finding.line_number,
                        "severity": finding.severity.value,
                        "type": finding.type.value,
                        "message": finding.message,
                        "suggested_fix": finding.suggested_fix,
                    },
                    ensure_ascii=False,
                )
            )
        tests_section = ", ".join(t.value for t in request.test_types)
        instructions = (
            "Generate concise automated test cases for the provided findings. "
            "Return JSON with a 'tests' array. Each test entry must include "
            "'finding_id', 'test_type', 'test_name', 'code', 'priority', "
            "'language', and 'framework'. Limit code to runnable pytest-style tests."
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are TraceFox Gemma, an assistant specialised in writing high-quality automated tests."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{instructions}\n\n"
                    f"Requested test types: {tests_section if tests_section else 'unit'}\n"
                    f"Findings JSON Lines:\n" + "\n".join(findings_section)
                ),
            },
        ]

    def _parse_generation_response(
        self,
        request: TestGenerationRequestPayload,
        response: Dict[str, Any],
        findings: List[Finding],
    ) -> List[TestCase]:
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("Missing choices in Gemma response")
        content = choices[0].get("message", {}).get("content", "")
        structured = self._safe_load_json(content)
        tests_payload = structured.get("tests", [])

        indexed_findings = {f.id: f for f in findings}
        generated: List[TestCase] = []
        for item in tests_payload:
            finding_id = item.get("finding_id")
            finding = indexed_findings.get(finding_id)
            if not finding:
                continue
            test_type_value = item.get("test_type") or request.test_types[0].value
            try:
                test_type = TestType(test_type_value)
            except ValueError:
                continue
            generated.append(
                TestCase(
                    id=str(uuid4()),
                    pull_request_id=request.pr_id,
                    finding_id=finding_id,
                    test_name=str(item.get("test_name") or f"{test_type.value}_test_{finding.file_path}"),
                    test_type=test_type,
                    test_code=str(item.get("code") or self._fallback_code(finding, test_type)),
                    priority=self._coerce_priority(item.get("priority")),
                    root_cause_mapping=f"Finding {finding_id}",
                    language=str(item.get("language") or "python"),
                    framework=str(item.get("framework") or "pytest"),
                )
            )
        return generated

    def _fallback_tests(
        self,
        request: TestGenerationRequestPayload,
        findings: List[Finding],
    ) -> List[TestCase]:
        generated: List[TestCase] = []
        for finding in findings:
            for test_type in request.test_types or [TestType.unit]:
                generated.append(
                    TestCase(
                        id=str(uuid4()),
                        pull_request_id=request.pr_id,
                        finding_id=finding.id,
                        test_name=f"{test_type.value}_test_{finding.file_path.replace('/', '_')}",
                        test_type=test_type,
                        test_code=self._fallback_code(finding, test_type),
                        priority=2,
                        root_cause_mapping=f"Finding {finding.id}",
                        language="python",
                        framework="pytest",
                    )
                )
        return generated

    def _fallback_code(self, finding: Finding, test_type: TestType) -> str:
        header = f"def test_{finding.id[:8]}_{test_type.value.replace('-', '_')}():"
        docstring = f'    """TraceFox fallback test for {finding.file_path}: {finding.message[:50]}..."""'
        body = f"    # TraceFox: This is a placeholder test for: {finding.message}\n    # Recommended fix: {finding.suggested_fix or 'Not provided'}\n    assert True"
        return "\n".join([header, docstring, body])

    def _safe_load_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    logger.debug("Unable to parse JSON from Gemma content: %s", content)
        return {}

    def _coerce_priority(self, candidate: Any) -> int:
        try:
            priority = int(candidate)
        except (TypeError, ValueError):
            priority = 2
        return max(1, min(priority, 5))
