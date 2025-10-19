from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.agent_orchestrator.orchestrator import DevGuardianOrchestrator
from services.event_processing.service import EventProcessingService


def main() -> None:
    orchestrator = DevGuardianOrchestrator()
    events = EventProcessingService(orchestrator=orchestrator)

    commit_response = events.handle_commit_event(
        {
            "commit_id": "abc1234",
            "repository": "devguardian/backend",
            "author": "sohail",
            "timestamp": datetime.utcnow().isoformat(),
            "files": [
                {
                    "path": "app/main.py",
                    "content": "def add(a, b):\n    return a + b\n",
                    "language": "python",
                },
                {
                    "path": "app/routes.py",
                    "content": "from fastapi import APIRouter\nrouter = APIRouter()\n",
                    "language": "python",
                },
            ],
        }
    )

    deployment_response = events.handle_deployment_event(
        {
            "deployment_id": "deploy-001",
            "commit_id": "abc1234",
            "environment": "production",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": [
                {"name": "latency_ms_p95", "value": 640.0, "unit": "ms"},
                {"name": "error_rate", "value": 0.045, "unit": "ratio"},
            ],
        }
    )

    print("=== Commit Response ===")
    print(commit_response)
    print("\n=== Deployment Response ===")
    print(deployment_response)


if __name__ == "__main__":
    main()
