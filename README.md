# TraceFox Control Center

TraceFox is the AI co-pilot for software delivery teams. We ingest pull-request activity, reason about code and tests, generate actionable insights, and close the loop with automated remediation. This repository bundles the v3 control center: a modular FastAPI backend, mission-control dashboard, and shared tooling designed to ship fast and scale with your team.

---

## Why TraceFox

- **Ship with confidence** – automated reviews and deterministic test generation catch regressions before they land.
- **Reduce firefighting** – flaky test detection and RCA summaries point engineers straight to the fix.
- **Operate transparently** – performance, ML drift, compliance, and feedback metrics are available in one mission-control UI.

TraceFox was built to be production-ready from day one: configuration via environment or config service, observability baked in, and services primed for cloud-native deployment.

---

## Architecture at a Glance

```
services/
  api_gateway/        # FastAPI entrypoint, fan-out to domain services
  code_indexing/      # Repo ingest + graph/embedding prep (simulated)
  review_engine/      # AI-powered PR analysis
  test_generation/    # Deterministic test synthesis
  test_execution/     # Parallel execution harness
  rca_engine/         # Root-cause intelligence + recommendations
  learning_feedback/  # Feedback capture + scoring
  compliance/         # Standards coverage reporting
  ml/                 # Drift detection heuristics
  shared/             # Config, event bus, connection pools, utilities
frontend/             # Next.js mission-control dashboard
infrastructure/       # Terraform + compose scaffolding
```

Each service is intentionally lightweight: swap the in-memory stores for your preferred persistence, plug in real model endpoints, and you’re production-ready without rewiring the architecture.

---

## Quickstart

1. **Clone & Create Env**
   ```bash
   git clone https://github.com/your-org/tracefox.git
   cd tracefox
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Configure Runtime**
   ```bash
   cp .env.example .env
   # edit .env or export via secrets manager
   ```
   All configuration lives behind the `TRACEFOX_` prefix. The sample file includes Redis, Neo4j, and Qdrant credentials that match `docker-compose.yml`.

3. **Launch Local Services**
   ```bash
   docker compose up -d redis neo4j qdrant
   uvicorn services.api_gateway.main:app --reload --port 8000
   ```

4. **Spin Up the Dashboard**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Visit `http://localhost:3000` to explore the mission-control experience.

---

## Developer Workflow

| Task | Command |
|------|---------|
| Run backend tests | `python3 -m pytest` |
| Run frontend tests | `cd frontend && npm run test` |
| Lint frontend | `cd frontend && npm run lint` |
| Sample webhook | see `docs/configuration.md` or use the in-app payload |

The main flow (`tests/test_api_gateway.py`) exercises the complete webhook → review → test generation → execution path to guard regressions.

---

## Configuration Matrix

Key environment knobs exposed via `services/shared/config.py`:

| Namespace | Highlights |
|-----------|------------|
| `TRACEFOX_POSTGRES__*` | Connection pooling, timeouts, statement limits |
| `TRACEFOX_REDIS__*` | Namespace versioning, TTLs, socket limits |
| `TRACEFOX_QDRANT__*` | Persistence, replication, backup schedules |
| `TRACEFOX_RETRY__*` / `TRACEFOX_CIRCUIT_BREAKER__*` | Backoff, jitter, breaker thresholds |
| `TRACEFOX_OBSERVABILITY__*` | OTLP endpoints, sampling ratios |
| `TRACEFOX_AI_MODELS__*` | Provider configs + default model temp |
| `TRACEFOX_QUALITY__FLAKY_THRESHOLD` | Default flaky-test gate |

Use `.env`, Vault/AppConfig, or any config service. Settings are cached but reloadable via `services.shared.config.reload_settings()`.

---

## Mission-Control UI

The dashboard showcases:

- **Pipeline Overview** – which stage (webhook, review, tests, execution, RCA) is active.
- **Operational Pulse** – live stats (active PR, pass rate, RCA count).
- **Onboarding Checklist** – first-time activation guidance.
- **Insights** – tabbed views for findings, generated tests, and RCA summaries.
- **Activity Feed** – toast-powered timeline of actions and alerts.

Everything is powered via SWR hooks that call the FastAPI gateway, with toast notifications and skeleton loading states to keep the experience smooth.

---

## Roadmap Snapshot

- **Today** – Full end-to-end storyline with simulators (AI review, tests, RCA), resilience primitives, event bus, and observability hooks.
- **Next** – Swap simulators for real integrations (embedding pipelines, CI runners, auth providers), add contract testing and production-ready storage.
- **Later** – Multi-tenant control planes, SSO/RBAC, advanced drift monitoring, and marketplace integrations.

Have ideas? Open a discussion or PR—we’re building TraceFox in the open.

---

## Support

Questions or integrations in mind?

- 📚 `docs/configuration.md` – deep-dive into config expectations.
- 🛠 Open an issue or join the TraceFox Slack.
- ✉️ hello@tracefox.ai – partnerships, pilots, or investor demos.

Let’s ship resilient software together. 🦊✨
