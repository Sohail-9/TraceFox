from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.agent_orchestrator.orchestrator import DevGuardianOrchestrator
from services.event_processing.service import EventProcessingService


class FilePayload(BaseModel):
    path: str
    content: str
    language: str = "python"


class CommitRequest(BaseModel):
    commit_id: str
    repository: str = "devguardian/demo"
    author: str = "unknown"
    timestamp: Optional[datetime] = None
    branch: str = "main"
    files: List[FilePayload]


class DeploymentMetric(BaseModel):
    name: str
    value: float
    unit: str = ""


class DeploymentRequest(BaseModel):
    deployment_id: str
    commit_id: str
    environment: str = "production"
    timestamp: Optional[datetime] = None
    metrics: List[DeploymentMetric] = []


app = FastAPI(title="DevGuardian Platform API", version="0.2.0")
orchestrator = DevGuardianOrchestrator()
event_service = EventProcessingService(orchestrator=orchestrator)


@app.post("/demo/run")
def run_demo(request: CommitRequest) -> Dict[str, Any]:
    return orchestrator.run_pipeline(
        commit_id=request.commit_id,
        files=[file.model_dump() for file in request.files],
    )


@app.post("/events/commit")
def commit_event(request: CommitRequest) -> Dict[str, Any]:
    payload = request.model_dump()
    if not payload["files"]:
        raise HTTPException(status_code=400, detail="No files supplied for analysis.")
    return event_service.handle_commit_event(payload)


@app.post("/events/deployment")
def deployment_event(request: DeploymentRequest) -> Dict[str, Any]:
    payload = request.model_dump()
    return event_service.handle_deployment_event(payload)


@app.get("/analytics/latest")
def latest_analytics() -> Dict[str, Any]:
    report = orchestrator.latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No analytics report available yet.")
    return report
