from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FileChange:
    path: str
    content: str
    language: str = "python"


@dataclass
class CommitEvent:
    commit_id: str
    repository: str
    author: str
    timestamp: datetime
    files: List[FileChange]
    branch: str = "main"


@dataclass
class FileAnalysis:
    path: str
    ast_summary: Dict[str, int]
    complexity_score: float
    risk_level: str
    warnings: List[str]
    embeddings_model: str
    embedding_ref: Optional[str] = None


@dataclass
class CodeAnalysisSummary:
    overall_risk: str
    average_complexity: float
    model_used: str


@dataclass
class GeneratedTestCase:
    name: str
    description: str
    priority: str
    suggested_assertions: List[str]
    model_selected: str
    confidence: float


@dataclass
class TestExecutionResult:
    name: str
    status: str
    duration_seconds: float
    log_excerpt: str
    retry_required: bool = False


@dataclass
class RootCauseAnalysis:
    failing_test: str
    explanation: str
    suggested_fix: str
    similar_incident: Optional[str]
    confidence: float
    model_selected: str


@dataclass
class NotificationMessage:
    channel: str
    body: str
    severity: str


@dataclass
class DeploymentEvent:
    deployment_id: str
    commit_id: str
    environment: str
    timestamp: datetime


@dataclass
class ProductionMetric:
    name: str
    value: float
    baseline: float
    unit: str


@dataclass
class AnomalyAlert:
    metric: str
    observed: float
    baseline: float
    severity: str
    methodology: str


@dataclass
class AnalyticsReport:
    commit_id: str
    tests_generated: int
    tests_failed: int
    notifications_sent: int
    anomalies_detected: int
    insights: List[str] = field(default_factory=list)

