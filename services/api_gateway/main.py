from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from services.agent_orchestrator.orchestrator import TraceFoxOrchestrator


class FilePayload(BaseModel):
    path: str
    content: str
    language: str = "python"


class CommitRequest(BaseModel):
    commit_id: str
    files: List[FilePayload]


app = FastAPI(title="TraceFox MVP API", version="0.1.0")
orchestrator = TraceFoxOrchestrator()


@app.post("/demo/run")
def run_demo(request: CommitRequest) -> Dict[str, Any]:
    return orchestrator.run_pipeline(
        commit_id=request.commit_id,
        files=[file.model_dump() for file in request.files],
    )
