"""Service registry coordinating API gateway calls to backend services."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Any, DefaultDict, Deque, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from services.code_indexing.service import CodebaseIndexingService, IndexingRequest
from services.code_indexing.git_repository_manager import GitRepositoryManager
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
    GitHubRepositorySummary,
    GitHubRepositoryTrackResponse,
    GitHubTrackedRepository,
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

        self._pr_registry: Dict[str, Dict[str, Any]] = {}
        self._tests_by_pr: DefaultDict[str, List[TestCase]] = defaultdict(list)
        self._test_index: Dict[str, TestCase] = {}
        self._executions_by_pr: DefaultDict[str, List[str]] = defaultdict(list)
        self._flaky_stats: DefaultDict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"pass": 0, "fail": 0, "flaky": 0})
        )
        self._execution_index: Dict[str, str] = {}
        self._activity: Deque[Dict[str, str]] = deque(maxlen=50)
        self._latest_pr_id: Optional[str] = None
        self._latest_execution_id: Optional[str] = None
        self.repositories = GitRepositoryManager(indexing_service=self.indexing)

    def _log_activity(self, *, tone: str, title: str, detail: str) -> None:
        self._activity.appendleft(
            {
                "id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "tone": tone,
                "title": title,
                "detail": detail,
            }
        )

    async def process_webhook(self, provider: str, payload: WebhookPayload) -> Dict[str, Any]:
        pr_id = self._pr_identifier(payload)
        payload_snapshot = payload.model_dump()
        self._pr_registry[pr_id] = {
            "provider": provider,
            "repository_id": payload.repository.id,
            "repository_name": payload.repository.name,
            "repository_url": str(payload.repository.url),
            "pull_request_number": payload.pull_request.number,
            "pull_request_title": payload.pull_request.title,
            "pull_request_author": payload.pull_request.author,
            "action": payload.action,
            "event_type": payload.event_type,
            "received_at": payload.timestamp.isoformat(),
            "payload": payload_snapshot,
        }
        self._latest_pr_id = pr_id

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
        self._log_activity(
            tone="success",
            title="Webhook processed",
            detail=f"PR {pr_id} via {provider} initiated review",
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
        self._log_activity(
            tone="info",
            title="Tests generated",
            detail=f"PR {request.pr_id}: {len(tests_cast)} test(s) prepared",
        )
        return {
            "job_id": job_id,
            "test_cases": [test_case.model_dump() for test_case in tests_cast],
            "total_generated": result.get("total_generated", len(tests_cast)),
        }

    async def list_tracked_repositories(self, user_id: str) -> Dict[str, Any]:
        return await self.repositories.list_tracked(user_id)

    async def onboard_repository(
        self,
        user_id: str,
        github_token: str,
        repo_payload: GitHubRepositorySummary,
    ) -> GitHubRepositoryTrackResponse:
        record = await self.repositories.register_repository(user_id, repo_payload.model_dump())
        clone_job = await self.repositories.schedule_clone(user_id=user_id, repo_data=repo_payload.model_dump(), github_token=github_token)
        repo_model = GitHubTrackedRepository.model_validate(record)
        return GitHubRepositoryTrackResponse(repository=repo_model, clone_job=clone_job)

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
        self._execution_index[execution_id] = request.pr_id
        self._latest_execution_id = execution_id
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
        tone = "success" if not failed_tests else "error"
        self._log_activity(
            tone=tone,
            title="Tests executed",
            detail=f"PR {request.pr_id}: {len(selected_tests)} run, {len(failed_tests)} failed",
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

    async def get_operations_snapshot(self) -> Dict[str, Any]:
        reviews = await self.review.all_reviews()
        total_reviews = len(reviews)
        total_findings = sum(review.total_findings for review in reviews)
        critical_total = sum(review.critical_count for review in reviews)
        major_total = sum(review.major_count for review in reviews)
        minor_total = sum(review.minor_count for review in reviews)
        summary_per_pr: Dict[str, Dict[str, Any]] = {}
        latest_review_info: Optional[Dict[str, Any]] = None
        if reviews:
            latest_review = max(reviews, key=lambda item: item.created_at)
            latest_review_info = {
                "pr_id": latest_review.pr_id,
                "summary": latest_review.summary,
                "total_findings": latest_review.total_findings,
                "critical_count": latest_review.critical_count,
                "major_count": latest_review.major_count,
                "minor_count": latest_review.minor_count,
                "created_at": latest_review.created_at.isoformat(),
            }
            for review in reviews:
                summary_per_pr[review.pr_id] = {
                    "review_id": review.review_id,
                    "summary": review.summary,
                    "total_findings": review.total_findings,
                    "critical": review.critical_count,
                    "major": review.major_count,
                    "minor": review.minor_count,
                    "created_at": review.created_at.isoformat(),
                }

        tests_total = sum(len(tests) for tests in self._tests_by_pr.values())
        tests_per_pr = {pr_id: len(tests) for pr_id, tests in self._tests_by_pr.items()}

        executions_total = sum(len(executions) for executions in self._executions_by_pr.values())
        executions_counts_per_pr = {pr_id: len(executions) for pr_id, executions in self._executions_by_pr.items()}
        executions_latest_per_pr: Dict[str, Dict[str, Any]] = {}
        rca_counts_per_pr: Dict[str, int] = {}
        rca_latest_per_pr: Dict[str, Dict[str, Any]] = {}

        for pr_id, execution_ids in self._executions_by_pr.items():
            if not execution_ids:
                continue
            latest_id = execution_ids[-1]
            latest_payload = await self.test_execution.get_execution(latest_id)
            if latest_payload:
                executions_latest_per_pr[pr_id] = {
                    "execution_id": latest_payload.get("execution_id"),
                    "status": latest_payload.get("status", "completed"),
                    "passed": latest_payload.get("passed", 0),
                    "failed": latest_payload.get("failed", 0),
                    "flaky": latest_payload.get("flaky", 0),
                    "skipped": latest_payload.get("skipped", 0),
                    "total_tests": latest_payload.get("total_tests", 0),
                    "execution_time_ms": latest_payload.get("execution_time_ms", 0),
                    "completed_at": latest_payload.get("completed_at"),
                }
            rca_count = 0
            latest_rca_entry: Optional[Dict[str, Any]] = None
            for exec_id in execution_ids:
                rca_payload = await self.rca.get_rca(exec_id)
                if not rca_payload:
                    continue
                rca_count += 1
                candidate = {
                    "execution_id": rca_payload.test_execution_id,
                    "category": rca_payload.category.value,
                    "summary": rca_payload.root_cause_summary,
                }
                latest_rca_entry = candidate
                if exec_id == latest_id:
                    break
            if rca_count:
                rca_counts_per_pr[pr_id] = rca_count
            if latest_rca_entry:
                rca_latest_per_pr[pr_id] = latest_rca_entry

        latest_execution_info: Optional[Dict[str, Any]] = None
        if self._latest_execution_id:
            latest_execution_payload = await self.test_execution.get_execution(self._latest_execution_id)
            if latest_execution_payload:
                latest_execution_info = {
                    "execution_id": latest_execution_payload.get("execution_id"),
                    "pr_id": self._execution_index.get(self._latest_execution_id),
                    "status": latest_execution_payload.get("status", "completed"),
                    "passed": latest_execution_payload.get("passed", 0),
                    "failed": latest_execution_payload.get("failed", 0),
                    "flaky": latest_execution_payload.get("flaky", 0),
                    "skipped": latest_execution_payload.get("skipped", 0),
                    "total_tests": latest_execution_payload.get("total_tests", 0),
                    "execution_time_ms": latest_execution_payload.get("execution_time_ms", 0),
                    "completed_at": latest_execution_payload.get("completed_at"),
                }

        rca_items = await self.rca.all_rca()
        rca_total = len(rca_items)
        latest_rca = None
        if self._latest_execution_id:
            latest_rca_payload = await self.rca.get_rca(self._latest_execution_id)
            if latest_rca_payload:
                latest_rca = {
                    "execution_id": latest_rca_payload.test_execution_id,
                    "category": latest_rca_payload.category.value,
                    "summary": latest_rca_payload.root_cause_summary,
                }
        quality_summary: Dict[str, Dict[str, int]] = {}
        for repo_id, tests in self._flaky_stats.items():
            aggregate = {"pass": 0, "fail": 0, "flaky": 0}
            for stats in tests.values():
                aggregate["pass"] += stats.get("pass", 0)
                aggregate["fail"] += stats.get("fail", 0)
                aggregate["flaky"] += stats.get("flaky", 0)
            quality_summary[repo_id] = aggregate

        activity_log = list(self._activity)

        latest_payload = None
        if self._latest_pr_id:
            latest_payload = self._pr_registry.get(self._latest_pr_id, {}).get("payload")

        return {
            "active_pr_id": self._latest_pr_id,
            "total_prs": len(self._pr_registry),
            "pr_registry": [
                {"pr_id": pr_id, **metadata} for pr_id, metadata in self._pr_registry.items()
            ],
            "summary": {
                "total_reviews": total_reviews,
                "total_findings": total_findings,
                "critical": critical_total,
                "major": major_total,
                "minor": minor_total,
                "latest": latest_review_info,
                "per_pr": summary_per_pr,
            },
            "tests": {
                "total_cases": tests_total,
                "per_pr": tests_per_pr,
            },
            "executions": {
                "total_runs": executions_total,
                "latest": latest_execution_info,
                "per_pr_counts": executions_counts_per_pr,
                "latest_per_pr": executions_latest_per_pr,
            },
            "rca": {
                "total": rca_total,
                "latest": latest_rca,
                 "per_pr_counts": rca_counts_per_pr,
                 "latest_per_pr": rca_latest_per_pr,
            },
            "quality": {
                "repositories": quality_summary,
            },
            "activity": activity_log,
            "checklist": {
                "webhook": bool(self._pr_registry),
                "review": total_reviews > 0,
                "tests": tests_total > 0,
                "execution": executions_total > 0,
            },
            "latest_payload": latest_payload,
        }

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
