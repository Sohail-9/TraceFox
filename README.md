DevGuardian is an AI-powered engineering intelligence platform that automates the full software development lifecycle. It blends open-source and premium AI models to analyse code, generate and execute tests, perform intelligent debugging, and connect production telemetry back to the originating commit. The repository contains a fully wired proof-of-concept that mirrors the architecture described in the DevGuardian technical design document.

## End-to-End Capabilities
- **Event intake**: Commit and deployment events enter through the FastAPI gateway and are normalised by the Event Processing service.
- **Code analysis**: Lightweight heuristics approximate CodeLlama/CodeBERT behaviour, emitting AST metrics, risk scores, and simulated embedding references. Krutrim DeepSeek R1 is the default base model.
- **Test generation**: Model routing emulates GPT-4, Claude, Krutrim, and Llama 3.1 selection to prioritise suggested test cases with Krutrim DeepSeek R1 as the primary option.
- **Execution & RCA**: Deterministic test execution feeds into an RCA engine backed by an in-memory knowledge base for similarity lookups.
- **Production monitoring**: Metric anomalies (latency, error rate, CPU) trigger alerts representing Isolation Forest/LSTM detection.
- **Notifications & analytics**: Slack/email summaries and an analytics report highlight failures, anomalies, and next actions.
- **User context & pricing tiers**: User Management returns plan entitlements and locale for model routing (e.g., Krutrim for Indian languages).
- **Web dashboard**: Next.js UI surfaces commit, deployment, and anomaly insights in real time.

## Project Structure
```
services/
  api_gateway/           # FastAPI entrypoints
  event_processing/      # Normalises and routes commit/deployment events
  agent_orchestrator/    # Coordinates the full DevGuardian workflow
  code_analysis/         # AST, risk scoring, embedding stubs
  test_generation/       # Test suggestions with model routing
  test_execution/        # Simulated execution outcomes
  debugging_service/     # RCA backed by knowledge base lookups
  knowledge_base/        # In-memory incident corpus
  notification_service/  # Slack/email style summaries
  production_monitor/    # Simple anomaly detection heuristics
  analytics/             # Aggregated insights for dashboards
  user_management/       # Plan, locale, and feature flag context
  common/                # Shared dataclasses, cache, and model router
scripts/run_demo.py      # Command-line runner exercising commit + deployment flows
requirements.txt         # FastAPI + uvicorn runtime dependencies
```
Python 3.10+ implicit namespace packages let us omit `__init__.py` files in the `services/` tree, keeping the layout closer to genuine microservice boundaries.

## Getting Started
1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the DevGuardian API:
   ```bash
   uvicorn services.api_gateway.main:app --reload
   ```

Alternatively, run the convenience script (sets Krutrim/DeepSeek defaults automatically):
```bash
scripts/deploy_local.sh
```

### Triggering Workflows via HTTP

**Commit event:**
```bash
curl -X POST http://localhost:8000/events/commit \
  -H "Content-Type: application/json" \
  -d '{
        "commit_id": "abc1234",
        "repository": "devguardian/backend",
        "author": "sohail",
        "files": [
          { "path": "app/main.py", "content": "def add(a, b):\n    return a + b\n" }
        ]
      }'
```

**Deployment event:**
```bash
curl -X POST http://localhost:8000/events/deployment \
  -H "Content-Type: application/json" \
  -d '{
        "deployment_id": "deploy-001",
        "commit_id": "abc1234",
        "environment": "production",
        "metrics": [
          { "name": "latency_ms_p95", "value": 640, "unit": "ms" },
          { "name": "error_rate", "value": 0.045, "unit": "ratio" }
        ]
      }'
```

**Latest analytics report:**
```bash
curl http://localhost:8000/analytics/latest
```

### CLI Demo
Run the scripted demo to simulate both commit and deployment flows without starting the API server:
```bash
python3 scripts/run_demo.py
```

### Container Image
Build and optionally push a Docker image:
```bash
scripts/build_image.sh
```
Override `IMAGE_NAME`, `IMAGE_TAG`, and `REGISTRY` to integrate with your registry.

## Infrastructure as Code
Terraform blueprints are provided for AWS (ECS Fargate) and Azure Container Apps. Both pass the Krutrim base model configuration into the runtime automatically.

### AWS (ECS Fargate)
```bash
IMAGE="123456789012.dkr.ecr.us-east-1.amazonaws.com/devguardian-api:latest" \
SUBNET_IDS='["subnet-abc","subnet-def"]' \
SG_IDS='["sg-123"]' \
terraform -chdir=infrastructure/aws apply \
  -var="region=us-east-1" \
  -var="image=${IMAGE}" \
  -var="subnet_ids=${SUBNET_IDS}" \
  -var="security_group_ids=${SG_IDS}"
```

Or use the helper script:
```bash
IMAGE=123456789012.dkr.ecr.us-east-1.amazonaws.com/devguardian-api:latest \
SUBNET_IDS='["subnet-abc","subnet-def"]' \
SG_IDS='["sg-123"]' \
ENVIRONMENT=staging \
scripts/deploy_aws.sh
```
`SUBNET_IDS` and `SG_IDS` must be valid JSON arrays pointing at existing VPC resources. Optional overrides: `CPU`, `MEMORY`, `DESIRED_COUNT`, `KRUTRIM_MODEL`, `KRUTRIM_API_BASE_URL`, `DEEPSEEK_ROUTER_MODEL`.

### Azure (Container Apps)
```bash
terraform -chdir=infrastructure/azure apply \
  -var="location=eastus" \
  -var="image=devguardian.azurecr.io/devguardian-api:latest"
```

Helper script:
```bash
IMAGE=devguardian.azurecr.io/devguardian-api:latest \
ENVIRONMENT=staging \
AZURE_LOCATION=eastus \
scripts/deploy_azure.sh
```
Optional overrides: `CPU`, `MEMORY_GB`, `MIN_REPLICAS`, `MAX_REPLICAS`, `KRUTRIM_MODEL`, `KRUTRIM_API_BASE_URL`, `DEEPSEEK_ROUTER_MODEL`.

Inputs such as subnet IDs, security groups, or registry credentials must already exist or be provisioned separately.

## Frontend Portal
The `frontend/` directory hosts a Next.js 14 dashboard styled with Tailwind CSS. It consumes the FastAPI endpoints to display pipeline state, notifications, and production anomalies for engineers and stakeholders.

### Install & Run
```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Or launch via the helper script:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 scripts/dev_frontend.sh
```
Ensure the FastAPI server is running on port `8000` (or adjust `NEXT_PUBLIC_API_BASE_URL`).

### Build for Deployment
```bash
cd frontend
npm run build
```
The static export is written to `frontend/out/` and can be served from a CDN or uploaded behind the API gateway's `/static` mount.

## Extending the Proof-of-Concept
- Replace heuristics with real model adapters (CodeLlama for AST, GPT-4/Claude for RCA, Krutrim for Indic coverage).
- Persist artefacts using PostgreSQL, MongoDB, TimescaleDB, and Pinecone/Weaviate as described in the design doc.
- Back the Event Processing service with Kafka or RabbitMQ and offload orchestration to Celery workers.
- Integrate actual Slack, Teams, Email providers and add RBAC/JWT authentication in the API gateway.
- Expand the analytics service to compute cohort metrics, cost projections, and SLA dashboards.

The current implementation is intentionally lightweight but demonstrates the full DevGuardian lifecycle from commit intake through production anomaly detection, ready to be swapped with production-grade components.
