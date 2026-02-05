"""Domain models shared across TraceFox services."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class FindingSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class FindingPriority(str, Enum):
    must_fix = "MUST_FIX"
    should_fix = "SHOULD_FIX"
    nice_to_fix = "NICE_TO_FIX"
    suppressed = "SUPPRESSED"


class FindingCategory(str, Enum):
    security = "security"
    performance = "performance"
    style = "style"
    logic = "logic"
    breaking_change = "breaking_change"
    cross_layer = "cross_layer"


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
    event_type: str = "pull_request"
    action: str
    repository: RepositoryInfo
    pull_request: PullRequestInfo
    files: List[FilePayload] = Field(default_factory=list)
    comment: Optional[str] = None
    comment_id: Optional[int] = None
    in_reply_to_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FindingSource(str, Enum):
    llama = "llama"
    deepseek = "deepseek"
    graph = "graph"
    orchestration = "orchestration"


class Finding(BaseModel):
    id: str
    type: FindingCategory
    severity: FindingSeverity
    confidence: float = Field(ge=0, le=1, default=0.5)
    message: str
    file_path: str
    line_number: int = 0
    suggested_fix: Optional[str] = None
    impact: Optional[str] = None
    source_model: Union[FindingSource, str] = FindingSource.llama
    metadata: Dict[str, Any] = Field(default_factory=dict)
    classification: Optional[Union[FindingPriority, str]] = None
    remediation: Optional[str] = None
    code_diff: Optional[str] = None


class AnalysisStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ReviewSummary(BaseModel):
    review_id: str
    pr_id: str
    repository: str
    pr_number: int
    summary: str
    findings: List[Finding]
    mermaid_diagram: Optional[str] = None
    total_findings: int = 0
    must_fix_count: int = 0
    should_fix_count: int = 0
    nice_to_fix_count: int = 0
    primary_model: str = "llama"
    duration_ms: int = 0
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


class PRAnalysisRequest(BaseModel):
    repository: str
    pr_number: int
    diff: str
    files: List[FilePayload] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    author: Optional[str] = None
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    repository_url: Optional[HttpUrl] = None


class RepositoryIndexRequest(BaseModel):
    repository_id: str
    repo_url: HttpUrl
    branch: str = "main"
    incremental: bool = False


class FileIndexRequest(BaseModel):
    repository_id: str
    repo_url: HttpUrl
    branch: str = "main"
    files: List[FilePayload] = Field(default_factory=list)


class FindingFeedbackRequest(BaseModel):
    user_id: str
    reaction: str
    comment: Optional[str] = None


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
