# TraceFox Backend (v3.0)

TraceFox is an AI-powered PR review and test intelligence platform that provides complete codebase context for pull requests, generates targeted tests from root-cause insights, and delivers persona-aware analytics. This repository contains the redesigned backend aligned with the TraceFox 3.0 design document, including service scaffolding for code indexing, AI reviews, test orchestration, RCA, compliance, and continuous learning.

## Architecture Overview

The backend follows a microservice-inspired layout built around FastAPI and asynchronous workers. Each domain exposes lightweight adapters and in-memory stores so the system can evolve towards production-grade integrations (PostgreSQL, Neo4j, LanceDB, Redis, RabbitMQ, etc.) without blocking day-to-day development.

```
services/
  api_gateway/              # FastAPI entrypoint exposing TraceFox REST APIs
  code_indexing/            # Repository cloning + AST/graph prep (simulated)
  review_engine/            # Multi-model PR analysis stubs
  test_generation/          # Targeted test synthesis from findings
  test_execution/           # Parallel execution + aggregation scaffolding
  rca_engine/               # Commit-correlation and RCA placeholder logic
  learning_feedback/        # Feedback capture + approval scoring
  compliance/               # Compliance coverage snapshots
  observability/            # Metric aggregation (in-memory)
  ml/                       # Data drift heuristics for ML pipelines
  shared/                   # Config, connection pools, domain models, event bus
```

Key interactions:
- Webhooks trigger indexing and AI review; findings are cached for PR retrieval.
- Generated tests feed the execution service, which tracks outcomes and notifies the RCA engine.
- RCA, flaky-test detection, compliance coverage, and drift detection surface via dedicated endpoints.
- Feedback updates learning metrics that inform future prioritisation.

## Prerequisites
- Python 3.10+
- (Optional) Local services for PostgreSQL, Redis, Neo4j, LanceDB if you want to wire real backends.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the API Gateway
```bash
uvicorn services.api_gateway.main:app --reload --port 8000
```

### Core Endpoints

| Method & Path | Description |
| ------------- | ----------- |
| `POST /webhooks/{provider}` | Intake PR webhooks (github/gitlab/bitbucket) and trigger indexing + review |
| `GET /reviews/pr/{pr_id}` | Retrieve AI review summary, optionally including generated tests or RCA |
| `POST /tests/generate` | Generate targeted tests for selected findings |
| `POST /tests/execute` | Execute tests in parallel containers (simulated) |
| `GET /tests/results/{execution_id}` | Fetch execution outcomes |
| `GET /rca/{test_execution_id}` | Fetch or trigger RCA for a failed execution |
| `GET /tests/flaky` | List flaky tests for a repository with threshold filters |
| `GET /compliance/{standard}` | Retrieve or seed compliance coverage snapshots |
| `POST /ml/drift/detect` | Run ML data drift detection heuristics |
| `POST /feedback` | Submit thumbs-up/down feedback for AI outputs |

#### Trigger a webhook
```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -d '{
        "event_type": "pull_request",
        "action": "opened",
        "repository": {
          "id": "repo-123",
          "name": "tracefox/backend",
          "url": "https://github.com/tracefox/backend",
          "default_branch": "main"
        },
        "pull_request": {
          "number": 42,
          "title": "Add payment compliance checks",
          "author": "sohail",
          "source_branch": "feature/compliance",
          "target_branch": "main",
          "diff_url": "https://github.com/tracefox/backend/pull/42.diff"
        }
      }'
```

#### Generate and execute tests
```bash
# Generate tests for the PR above
curl -X POST http://localhost:8000/tests/generate \
  -H "Content-Type: application/json" \
  -d '{
        "pr_id": "repo-123:42",
        "finding_ids": [],
        "test_types": ["unit", "integration"],
        "prioritize": true
      }'

# Execute tests using returned identifiers
curl -X POST http://localhost:8000/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
        "pr_id": "repo-123:42",
        "test_case_ids": ["<test-id-1>", "<test-id-2>"],
        "parallel": true,
        "timeout_seconds": 300
      }'
```

#### Fetch downstream insights
```bash
curl http://localhost:8000/reviews/pr/repo-123:42?include_tests=true&include_rca=true
curl http://localhost:8000/tests/results/<execution-id>
curl http://localhost:8000/rca/<execution-id>
curl http://localhost:8000/tests/flaky?repository_id=repo-123&threshold=0.25
curl http://localhost:8000/compliance/pci_dss?repository_id=repo-123
```

### Configuration
Environment variables can be prefixed with `TRACEFOX_` to override defaults in `services/shared/config.py`. Examples:

```bash
export TRACEFOX_ENVIRONMENT=local
export TRACEFOX_POSTGRES__HOST=localhost
export TRACEFOX_REDIS__HOST=localhost
export TRACEFOX_NEO4J__URI=neo4j://localhost:7687
```

## Roadmap Alignment
- **Phase 1 (MVP)**: API gateway, indexing, review, test generation/execution, and RCA skeletons are implemented here.
- **Phase 2 (Differentiation)**: Stubs exist for flaky test management, ML drift detection, compliance mapping, and feedback loops.
- **Phase 3 (Enterprise)**: Configuration and service boundaries are structured to plug into SSO, RBAC, observability, and multi-region deployments described in the design document.

## Next Steps
- Wire actual PostgreSQL/Redis/Neo4j/LanceDB clients inside `services/shared/database.py` and replace in-memory stores.
- Replace heuristic data generation with real AST parsing, embedding generation, and multi-model inference.
- Extend `services/observability` to emit traces/metrics via OpenTelemetry (Jaeger/Prometheus).
- Integrate message brokers (RabbitMQ/Kafka) using the `event_bus` abstraction.
- Harden the testing story with pytest suites per service and contract tests across the API gateway.

## Frontend
The `frontend/` directory still contains the existing Next.js portal. Update its API calls to align with the new endpoints when ready.

