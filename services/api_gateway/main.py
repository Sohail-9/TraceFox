from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from services.api_gateway.routes.auth import require_user, router as auth_router
from services.api_gateway.routes.github import router as github_router
from services.api_gateway.service_registry import TraceFoxServiceRegistry, registry
from services.shared.auth import AuthenticatedUser
from services.shared.config import ConfigurationError, get_settings
from services.shared.logging import setup_logging
from services.shared.observability import observability
from services.shared.models import (
    DriftDetectionRequest,
    FeedbackPayload,
    FileIndexRequest,
    FindingFeedbackRequest,
    PRAnalysisRequest,
    RepositoryIndexRequest,
    TestExecutionRequest,
    TestGenerationRequestPayload,
    WebhookPayload,
)

setup_logging()

observability.configure("api-gateway")
settings = get_settings()

app = FastAPI(
    title="TraceFox API Gateway",
    version="3.0.0",
    description="Entry point for TraceFox backend services.",
)

if settings.environment == "development":
    allowed_origins = ["*"]
    allow_creds = True
else:
    allowed_origins = list(settings.api_gateway_allowed_origins or [])
    if not allowed_origins:
        allowed_origins = ["*"]
        allow_creds = False
    else:
        allow_creds = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=allow_creds,  # Dynamic credential allowance
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

observability.instrument_fastapi(app)
app.include_router(auth_router)
app.include_router(github_router)


def get_registry() -> TraceFoxServiceRegistry:
    return registry


from services.shared.security import validate_webhook_signature

@app.post("/webhooks/{provider}", status_code=status.HTTP_202_ACCEPTED)
async def handle_webhook(
    provider: str,
    payload: WebhookPayload,
    signature: str = Header(None, alias="X-Hub-Signature-256"),
    event_type: str = Header("pull_request", alias="X-GitHub-Event"),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    # Inject event type from header if not explicitly set in body
    payload.event_type = event_type
    
    if not validate_webhook_signature(provider, payload, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )
    return await svc.process_webhook(provider, payload)


@app.options("/webhooks/{provider}")
async def webhook_preflight(provider: str) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/index/repository", status_code=status.HTTP_202_ACCEPTED)
async def index_repository(
    request: RepositoryIndexRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.index_repository(request)


@app.post("/api/v1/index/files", status_code=status.HTTP_202_ACCEPTED)
async def index_files(
    request: FileIndexRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.index_files(request)


@app.get("/operations/console")
async def get_operations_console(
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_operations_snapshot()


@app.get("/reviews/pr/{pr_id}")
async def get_pr_review(
    pr_id: str = Path(..., description="Pull request identifier"),
    include_tests: bool = Query(False),
    include_rca: bool = Query(False),
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_pr_review(pr_id, include_tests, include_rca)


@app.post("/api/v1/analyze/pr", status_code=status.HTTP_202_ACCEPTED)
async def analyze_pr(
    request: PRAnalysisRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.analyze_pull_request(request)


@app.post("/tests/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_tests(
    request: TestGenerationRequestPayload,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.generate_tests(request)


@app.post("/tests/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_tests(
    request: TestExecutionRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    if not request.test_case_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No test case ids provided")
    return await svc.execute_tests(request)


@app.get("/tests/results/{execution_id}")
async def get_test_results(
    execution_id: str,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_test_results(execution_id)


@app.get("/rca/{test_execution_id}")
async def get_rca(
    test_execution_id: str,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_rca(test_execution_id)


@app.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackPayload,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.submit_feedback(payload)


@app.post("/api/v1/feedback/{finding_id}", status_code=status.HTTP_201_CREATED)
async def submit_feedback_for_finding(
    finding_id: str,
    request: FindingFeedbackRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    payload = FeedbackPayload(
        user_id=request.user_id,
        target_type="finding",
        target_id=finding_id,
        reaction=request.reaction,
        comment=request.comment,
    )
    return await svc.submit_feedback(payload)


@app.get("/tests/flaky")
async def list_flaky_tests(
    repository_id: str = Query(...),
    threshold: float | None = Query(None, ge=0.0, le=1.0),
    is_quarantined: bool | None = Query(None),
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    effective_threshold = threshold
    if effective_threshold is None:
        try:
            effective_threshold = get_settings().quality.flaky_threshold
        except ConfigurationError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Flaky test threshold configuration missing"
            ) from exc
    return await svc.list_flaky_tests(repository_id, effective_threshold, is_quarantined)


@app.get("/compliance/{standard}")
async def get_compliance_report(
    standard: str,
    repository_id: str = Query(...),
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.get_compliance(standard, repository_id)


@app.post("/ml/drift/detect", status_code=status.HTTP_202_ACCEPTED)
async def detect_data_drift(
    request: DriftDetectionRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    svc: TraceFoxServiceRegistry = Depends(get_registry),
) -> dict:
    return await svc.detect_drift(request)


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "ok"}
