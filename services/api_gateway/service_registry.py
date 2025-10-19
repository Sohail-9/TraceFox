"""Service registry coordinating API gateway calls to backend services."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from services.code_indexing.service import CodebaseIndexingService, IndexingRequest
from services.compliance.service import ComplianceService
from services.learning_feedback.service import LearningFeedbackService
from services.ml.service import DriftDetectionService
from services.rca_engine.service import RCAEngine
from services.review_engine.service import AIReviewEngine
from services.shared.event_bus import event_bus
from services.shared.resilience import execute_with_resilience
from services.shared.models import (
    DriftDetectionRequest,
    FeedbackPayload,
    TestCase,
    TestExecutionRequest,
    TestGenerationRequestPayload,
    WebhookPayload,
)
from services.test_execution.service import TestExecutionService
from services.test_generation.service import TestGenerationService


class TraceFoxServiceRegistry:
    """Facade for coordinating calls to underlying service domains."""

    def __init__(self) -> None:
        self.indexing = CodebaseIndexingService()
        self.review = AIReviewEngine()
        self.test_generation = TestGenerationService()
        self.test_execution = TestExecutionService()
        self.rca = RCAEngine()
        self.learning = LearningFeedbackService()
        self.compliance = ComplianceService()
        self.drift = DriftDetectionService()

        self._pr_registry: Dict[str, Dict[str, str]] = {}
        self._tests_by_pr: DefaultDict[str, List[TestCase]] = defaultdict(list)
        self._test_index: Dict[str, TestCase] = {}
        self._executions_by_pr: DefaultDict[str, List[str]] = defaultdict(list)
        self._flaky_stats: DefaultDict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"pass": 0, "fail": 0, "flaky": 0})
        )

    async def process_webhook(self, provider: str, payload: WebhookPayload) -> Dict[str, Any]:
        pr_id = self._pr_identifier(payload)
        self._pr_registry[pr_id] = {
            "provider": provider,
            "repository_id": payload.repository.id,
        }

        indexing_job = await self.indexing.queue_indexing(
            IndexingRequest(
                repository_id=payload.repository.id,
                repo_url=str(payload.repository.url),
                branch=payload.repository.default_branch,
                incremental=payload.action == "synchronize",
            )
        )
        review_summary = await execute_with_resilience(
            "ai-review.run",
            self.review.run_review,
            pr_id,
            payload,
        )
        await event_bus.publish(
            "api:webhook",
            {"provider": provider, "pr_id": pr_id, "review_id": review_summary.review_id},
        )
        return {
            "status": "accepted",
            "job_id": indexing_job.job_id,
            "message": "PR review initiated",
            "review_id": review_summary.review_id,
        }

    async def get_pr_review(
        self, pr_id: str, include_tests: bool, include_rca: bool
    ) -> Dict[str, Any]:
        review = await self.review.get_review(pr_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review {pr_id} not found",
            )
        payload = review.model_dump()
        if include_tests:
            payload["tests"] = [test.model_dump() for test in self._tests_by_pr.get(pr_id, [])]
        if include_rca:
            executons = self._executions_by_pr.get(pr_id, [])
            rca_items = []
            for execution_id in executons:
                rca = await self.rca.get_rca(execution_id)
                if rca:
                    rca_items.append(rca.model_dump())
            payload["rca"] = rca_items
        return payload

    async def generate_tests(self, request: TestGenerationRequestPayload) -> Dict[str, Any]:
        review = await self.review.get_review(request.pr_id)
        result = await execute_with_resilience(
            "test-generation.generate",
            self.test_generation.generate_tests,
            request,
            review,
        )
        tests = result.get("tests", [])
        tests_cast: List[TestCase] = []
        for test in tests:
            if isinstance(test, TestCase):
                tests_cast.append(test)
            else:
                tests_cast.append(TestCase.model_validate(test))
        self._tests_by_pr[request.pr_id].extend(tests_cast)
        for test_case in tests_cast:
            self._test_index[test_case.id] = test_case
        job_id = str(uuid4())
        await event_bus.publish(
            "tests:generate",
            {"pr_id": request.pr_id, "job_id": job_id, "total": result.get("total_generated", 0)},
        )
        return {
            "job_id": job_id,
            "test_cases": [test_case.model_dump() for test_case in tests_cast],
            "total_generated": result.get("total_generated", len(tests_cast)),
        }

    async def execute_tests(self, request: TestExecutionRequest) -> Dict[str, Any]:
        available_tests = self._tests_by_pr.get(request.pr_id, [])
        lookup = {test.id: test for test in available_tests}
        selected_tests = []
        for test_id in request.test_case_ids:
            test = lookup.get(test_id) or self._test_index.get(test_id)
            if not test:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Test case {test_id} not found")
            selected_tests.append(test)

        execution_summary = await execute_with_resilience(
            "test-execution.run",
            self.test_execution.execute,
            request,
            selected_tests,
        )
        execution_id = execution_summary["execution_id"]
        full_result = await self.test_execution.get_execution(execution_id)
        assert full_result is not None  # nosec - ensured by execute

        repository_id = self._repository_for_pr(request.pr_id)
        self._executions_by_pr[request.pr_id].append(execution_id)
        for result in full_result["results"]:
            stats = self._flaky_stats[repository_id][result["test_case_id"]]
            status_key = {
                "passed": "pass",
                "failed": "fail",
                "flaky": "flaky",
            }.get(result["status"], "pass")
            stats[status_key] += 1
            matched = next((t for t in selected_tests if t.id == result["test_case_id"]), None)
            if matched:
                self._test_index[result["test_case_id"]] = matched

        failed_tests = [
            result for result in full_result["results"] if result["status"] == "failed"
        ]
        if failed_tests:
            await execute_with_resilience(
                "rca.analyse",
                self.rca.analyse,
                execution_id,
                failed_tests,
            )

        execution_summary["results_url"] = f"/tests/results/{execution_id}"
        await event_bus.publish(
            "tests:execute",
            {
                "execution_id": execution_id,
                "pr_id": request.pr_id,
                "total_tests": len(selected_tests),
                "failed": len(failed_tests),
            },
        )
        return execution_summary

    async def get_test_results(self, execution_id: str) -> Dict[str, Any]:
        execution = await self.test_execution.get_execution(execution_id)
        if not execution:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
        return execution

    async def get_rca(self, execution_id: str) -> Dict[str, Any]:
        rca = await self.rca.get_rca(execution_id)
        if rca:
            return rca.model_dump()
        execution = await self.test_execution.get_execution(execution_id)
        if not execution:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
        failed_tests = [result for result in execution["results"] if result["status"] == "failed"]
        if not failed_tests:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No failures to analyse")
        new_rca = await self.rca.analyse(execution_id, failed_tests)
        if not new_rca:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Unable to generate RCA")
        return new_rca.model_dump()

    async def submit_feedback(self, feedback: FeedbackPayload) -> Dict[str, Any]:
        await self.learning.record_feedback(feedback)
        aggregates = await self.learning.aggregate_scores(feedback.target_id)
        feedback_id = f"feedback-{uuid4()}"
        await event_bus.publish("feedback", {"feedback_id": feedback_id, **feedback.model_dump()})
        return {
            "feedback_id": feedback_id,
            "message": "Feedback recorded successfully",
            "aggregates": aggregates,
        }

    async def list_flaky_tests(
        self, repository_id: str, threshold: float, is_quarantined: Optional[bool]
    ) -> Dict[str, Any]:
        repo_stats = self._flaky_stats.get(repository_id, {})
        flaky_tests = []
        for test_case_id, stats in repo_stats.items():
            total_runs = sum(stats.values())
            if total_runs == 0:
                continue
            flaky_score = stats["flaky"] / total_runs
            if flaky_score >= threshold:
                test_case = self._test_index.get(test_case_id)
                flaky_tests.append(
                    {
                        "test_case_id": test_case_id,
                        "test_name": test_case.test_name if test_case else test_case_id,
                        "flaky_score": round(flaky_score, 2),
                        "pass_count": stats["pass"],
                        "fail_count": stats["fail"],
                        "total_runs": total_runs,
                        "last_flaky_at": None,
                        "is_quarantined": False if is_quarantined is None else is_quarantined,
                        "fix_suggestion": "Investigate timing dependencies and increase stabilization.",
                    }
                )
        if is_quarantined is not None:
            flaky_tests = [test for test in flaky_tests if test["is_quarantined"] == is_quarantined]
        return {"flaky_tests": flaky_tests, "total_flaky": len(flaky_tests), "threshold": threshold}

    async def get_compliance(self, standard: str, repository_id: str) -> Dict[str, Any]:
        report = await self.compliance.get_report(standard, repository_id)
        if not report:
            report = await self.compliance.seed_default_report(standard, repository_id)
        return report.model_dump()

    async def detect_drift(self, request: DriftDetectionRequest) -> Dict[str, Any]:
        result = await self.drift.detect(request)
        await event_bus.publish("ml:drift", {"pr_id": request.pr_id, "drift": result})
        return result

    def _pr_identifier(self, payload: WebhookPayload) -> str:
        return f"{payload.repository.id}:{payload.pull_request.number}"

    def _repository_for_pr(self, pr_id: str) -> str:
        metadata = self._pr_registry.get(pr_id)
        if not metadata:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown PR context")
        return metadata["repository_id"]


registry = TraceFoxServiceRegistry()
