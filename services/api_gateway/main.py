from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status

from services.api_gateway.service_registry import TraceFoxServiceRegistry, registry
from services.shared.config import ConfigurationError, get_settings
from services.shared.logging import setup_logging
from services.shared.observability import observability
from services.shared.models import (
    DriftDetectionRequest,
    FeedbackPayload,
    TestExecutionRequest,
    TestGenerationRequestPayload,
    WebhookPayload,
)

setup_logging()

observability.configure("api-gateway")

app = FastAPI(
    title="TraceFox API Gateway",
    version="3.0.0",
    description="Entry point for TraceFox backend services.",
)

observability.instrument_fastapi(app)


def get_registry() -> TraceFoxServiceRegistry:
    return registry


@app.post("/webhooks/{provider}", status_code=status.HTTP_202_ACCEPTED)
async def handle_webhook(
    provider: str,
    payload: WebhookPayload,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.process_webhook(provider, payload)


@app.get("/reviews/pr/{pr_id}")
async def get_pr_review(
    pr_id: str = Path(..., description="Pull request identifier"),
    include_tests: bool = Query(False),
    include_rca: bool = Query(False),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_pr_review(pr_id, include_tests, include_rca)


@app.post("/tests/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_tests(
    request: TestGenerationRequestPayload,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.generate_tests(request)


@app.post("/tests/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_tests(
    request: TestExecutionRequest,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    if not request.test_case_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No test case ids provided")
    return await svc.execute_tests(request)


@app.get("/tests/results/{execution_id}")
async def get_test_results(
    execution_id: str,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_test_results(execution_id)


@app.get("/rca/{test_execution_id}")
async def get_rca(
    test_execution_id: str,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_rca(test_execution_id)


@app.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackPayload,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.submit_feedback(payload)


@app.get("/tests/flaky")
async def list_flaky_tests(
    repository_id: str = Query(...),
    threshold: float | None = Query(None, ge=0.0, le=1.0),
    is_quarantined: bool | None = Query(None),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    effective_threshold = threshold
    if effective_threshold is None:
        try:
            effective_threshold = get_settings().quality.flaky_threshold
        except ConfigurationError as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc
    return await svc.list_flaky_tests(repository_id, effective_threshold, is_quarantined)


@app.get("/compliance/{standard}")
async def get_compliance_report(
    standard: str,
    repository_id: str = Query(...),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_compliance(standard, repository_id)


@app.post("/ml/drift/detect", status_code=status.HTTP_202_ACCEPTED)
async def detect_data_drift(
    request: DriftDetectionRequest,
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.detect_drift(request)


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "ok"}
