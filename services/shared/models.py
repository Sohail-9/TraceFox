"""Domain models shared across TraceFox services."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Severity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"


class FindingCategory(str, Enum):
    security = "security"
    performance = "performance"
    bug = "bug"
    style = "style"
    test_gap = "test_gap"


class TestType(str, Enum):
    unit = "unit"
    integration = "integration"
    e2e = "e2e"
    security = "security"
    performance = "performance"


class RCACategory(str, Enum):
    logic = "logic"
    data = "data"
    environment = "environment"
    infrastructure = "infrastructure"
    dependency = "dependency"


class FilePayload(BaseModel):
    path: str
    content: str
    language: str = "python"


class RepositoryInfo(BaseModel):
    id: str
    name: str
    url: HttpUrl
    default_branch: str = "main"


class PullRequestInfo(BaseModel):
    number: int
    title: str
    author: str
    source_branch: str
    target_branch: str
    diff_url: HttpUrl


class WebhookPayload(BaseModel):
    event_type: str
    action: str
    repository: RepositoryInfo
    pull_request: PullRequestInfo
    files: List[FilePayload] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReviewFinding(BaseModel):
    id: str
    file_path: str
    line_number: int
    severity: Severity
    category: FindingCategory
    description: str
    suggested_fix: Optional[str] = None
    code_diff: Optional[str] = None
    confidence_score: float = Field(ge=0, le=1, default=0.5)


class ReviewSummary(BaseModel):
    review_id: str
    pr_id: str
    summary: str
    findings: List[ReviewFinding]
    mermaid_diagram: Optional[str] = None
    total_findings: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TestCase(BaseModel):
    id: str
    pull_request_id: str
    finding_id: Optional[str] = None
    test_name: str
    test_type: TestType
    test_code: str
    priority: int = Field(ge=1, le=5)
    root_cause_mapping: Optional[str] = None
    language: str = "python"
    framework: str = "pytest"


class TestGenerationRequestPayload(BaseModel):
    pr_id: str
    finding_ids: List[str]
    test_types: List[TestType]
    prioritize: bool = True


class TestExecutionRequest(BaseModel):
    pr_id: str
    test_case_ids: List[str]
    parallel: bool = True
    timeout_seconds: int = Field(300, ge=60, le=1800)


class TestExecutionResult(BaseModel):
    execution_id: str
    test_case_id: str
    test_name: str
    status: str
    execution_time_ms: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


class RCAFinding(BaseModel):
    id: str
    test_execution_id: str
    category: RCACategory
    root_cause_summary: str
    root_cause_details: dict
    correlated_commits: List[dict] = Field(default_factory=list)
    suggested_fixes: List[dict] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.5)
    prevention_recommendations: List[str] = Field(default_factory=list)


class FeedbackPayload(BaseModel):
    user_id: str
    target_type: str
    target_id: str
    reaction: str
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ComplianceRequirement(BaseModel):
    requirement_id: str
    description: str
    status: str
    test_cases: List[str]
    recommendation: Optional[str] = None


class ComplianceReport(BaseModel):
    standard: str
    total_requirements: int
    covered_requirements: int
    coverage_percentage: float
    requirements: List[ComplianceRequirement]


class DriftMetrics(BaseModel):
    drift_detected: bool
    metrics: dict
    recommendations: List[str]


class DriftDetectionRequest(BaseModel):
    pr_id: str
    pipeline_type: str
    reference_data_url: str
    current_data_url: str
    features: List[str] = Field(default_factory=list)


class GitHubRepositoryOwner(BaseModel):
    login: str


class GitHubRepositorySummary(BaseModel):
    id: int
    full_name: str
    description: Optional[str] = None
    clone_url: str
    default_branch: str
    html_url: str
    private: bool
    owner: GitHubRepositoryOwner


class GitHubTrackedRepository(BaseModel):
    repo_id: int
    full_name: str
    description: Optional[str] = None
    clone_url: str
    default_branch: str
    html_url: str
    private: bool
    clone_path: Optional[str] = None
    sync_status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GitHubCloneJob(BaseModel):
    job_id: str
    full_name: str
    status: str
    message: Optional[str] = None
    clone_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GitHubRepositoryTrackResponse(BaseModel):
    repository: GitHubTrackedRepository
    clone_job: Dict[str, Any]
