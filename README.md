# 🦊 TraceFox: AI Co-pilot for Software Delivery

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green?style=flat-square&logo=fastapi)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue?style=flat-square&logo=typescript)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)]()
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

**End-to-end visibility from pull request to production.** AI-powered code review, intelligent test generation, flaky test detection, and RCA—all in one control center.

[📖 Documentation](#documentation) • [🚀 Quickstart](#quickstart) • [🏗️ Architecture](#architecture) • [🛣️ Roadmap](#roadmap)

</div>

---

## Why TraceFox?

Modern engineering teams need more than tools—they need a co-pilot. TraceFox automates the entire SDLC feedback loop:

✨ **Ship with confidence**  
Automated PR reviews and deterministic test generation catch regressions *before* they land.

🔍 **Reduce firefighting**  
Flaky test detection and root cause analysis summaries point engineers straight to the fix—not the symptom.

📊 **Operate transparently**  
One mission-control UI surfaces pipeline health, quality gates, performance trends, and ML drift in real-time.

🚀 **Built for production from day one**  
Cloud-native architecture, environment-driven config, built-in observability, and resilience primitives.

---

## Who is This For?

### 👨‍💼 Staff/Platform Engineers
- **Need**: Standardized, opinionated quality gates across repos  
- **Get**: Automated enforcement of best practices, flaky test dashboards, and compliance reporting

### 🛠️ DevOps / Engineering Effectiveness Teams
- **Need**: Unified visibility into test health and incident patterns  
- **Get**: RCA-powered insights, per-repo quality trends, and actionable alerts

### 🚀 Startup CTOs / Early-Stage Product Teams
- **Need**: Rapid velocity without sacrificing reliability  
- **Get**: End-to-end demo with simulators (no infra required) + one-command bootstrap

---

## Architecture: Modular & Extensible

```
TraceFox Control Plane (v3)
├── API Gateway (FastAPI)
│   └── Webhook ingestion, PR events, health checks
├── Domain Services (Microservices)
│   ├── code_indexing      — Repository metadata, graph prep
│   ├── review_engine      — AI-powered code analysis
│   ├── test_generation    — Deterministic test synthesis
│   ├── test_execution     — Parallel execution harness
│   ├── rca_engine         — Root cause intelligence
│   ├── learning_feedback  — Feedback capture & scoring
│   ├── compliance         — Standards & audit trail
│   └── ml                 — Drift detection heuristics
├── Shared Layer
│   ├── Event Bus (Redis)
│   ├── Persistence (PostgreSQL + SQLite)
│   ├── Embeddings & Graph (Qdrant + Neo4j)
│   └── Config, Observability, Resilience
└── Frontend (Next.js)
    └── Mission-Control Dashboard (SWR + Toast notifications)
```

**Each service is intentionally lightweight**: swap simulators for real integrations (embedding pipelines, CI runners) without rewiring core logic.

---

## Pipeline in Action

```
1. Pull Request Created
   ↓
2. GitHub Webhook → API Gateway
   ↓
3. Code Review Engine (AI analysis, findings)
   ↓
4. Test Generation (coverage gaps, edge cases)
   ↓
5. Test Execution (parallel harness, flaky detection)
   ↓
6. RCA Summary (if failures detected)
   ↓
7. Findings Posted to PR (structured comments, quality gate)
   ↓
8. Metrics Aggregated in Dashboard
```

---

## Quickstart

### 1️⃣ Clone & Setup

```bash
git clone https://github.com/Sohail-9/tracefox.git
cd tracefox
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2️⃣ Configure Environment

```bash
cp .env.example .env
# Edit .env with your GitHub + AI model credentials
```

**Key environment variables:**

| Variable | Purpose | Example |
|----------|---------|----------|
| `TRACEFOX_GITHUB__CLIENT_ID` | GitHub OAuth app | `Ov1.xxxxx` |
| `TRACEFOX_GITHUB__CLIENT_SECRET` | GitHub OAuth secret | (from app settings) |
| `TRACEFOX_AUTH__GITHUB__DEV_MODE` | Local stub login (dev only) | `true` |
| `TRACEFOX_REDIS__URL` | Redis endpoint | `redis://localhost:6379` |
| `TRACEFOX_POSTGRES__URL` | Postgres connection | `postgresql://...` |

See [`docs/configuration.md`](#configuration) for the full matrix.

### 3️⃣ Start Local Services

```bash
# Bring up Postgres, Redis, Neo4j, Qdrant
docker compose up -d postgres redis neo4j qdrant

# Start the FastAPI backend
uvicorn services.api_gateway.main:app --reload --port 8000
```

### 4️⃣ Launch the Dashboard

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

**Visit** `http://localhost:3000` to explore the mission-control experience.

> **Tip**: For local development without real GitHub OAuth, set `TRACEFOX_AUTH__GITHUB__DEV_MODE=true` and use the `/auth/github/dev-login` endpoint.

---

## Developer Workflow

| Task | Command |
|------|----------|
| Run backend tests | `python -m pytest` |
| Run frontend tests | `cd frontend && npm run test` |
| Lint frontend | `cd frontend && npm run lint` |
| Format code | `black services/ && npm --prefix frontend run format` |
| Sample webhook payload | See `docs/configuration.md` or in-app uploader |

**Main integration test:** `tests/test_api_gateway.py` exercises the complete webhook → review → test generation → RCA path.

---

## Configuration Deep Dive

TraceFox uses a hierarchical config system: environment variables → config service → defaults.

All settings live behind the `TRACEFOX_` prefix and are exposed via `services/shared/config.py`:

### Database & Persistence

```
TRACEFOX_POSTGRES__*         Connection pooling, statement limits, timeouts
TRACEFOX_REDIS__*            Namespacing, TTLs, socket config
TRACEFOX_QDRANT__*           Vector storage, replication schedules
TRACEFOX_NEO4J__*            Graph persistence, driver options
```

### Resilience & Performance

```
TRACEFOX_RETRY__*            Backoff strategy, max attempts, jitter
TRACEFOX_CIRCUIT_BREAKER__*  Failure thresholds, half-open timeouts
```

### AI & Quality Gates

```
TRACEFOX_AI_MODELS__*        Model providers, temperature, context length
TRACEFOX_QUALITY__*          Flaky thresholds, coverage minimums
```

### Observability

```
TRACEFOX_OBSERVABILITY__*    OTLP endpoints, sampling ratios, correlation IDs
```

💡 Settings are cached but reloadable via `services.shared.config.reload_settings()`.

---

## Mission-Control Dashboard

The frontend showcases:

- **Pipeline Overview** — Real-time stage visibility (webhook → review → tests → RCA)
- **Operational Pulse** — Live metrics: active PRs, test pass rate, flaky count
- **Onboarding Checklist** — First-time setup guidance (dismissible)
- **Insights Hub** — Tabbed views for findings, generated tests, RCA summaries
- **Activity Feed** — Toast-powered event timeline with drill-down

Every view is powered by SWR hooks that call the FastAPI gateway, with skeleton loading and error boundaries.

---

## Roadmap

### ✅ Today (v3)
End-to-end storyline with simulators, resilience primitives, event bus, observability hooks, and production-ready architecture.

### 🚧 Next (v3.1 - v4)
- Real integrations: embedding pipelines, CI runners (GitHub Actions, GitLab CI), model providers
- Contract testing and breaking-change detection
- Multi-repository dashboard (org-wide health)
- Secrets scanning integration

### 🔮 Later (v5+)
- Multi-tenant control planes with RBAC/SSO
- Advanced drift monitoring and anomaly detection
- Marketplace for custom review rules and test generators
- Slack/Teams integration with actionable notifications
- Kubernetes-native deployment (Helm charts)

---

## Testing

### Backend

```bash
python -m pytest tests/ -v
```

### Frontend

```bash
cd frontend && npm run test
```

### End-to-End

The main flow in `tests/test_api_gateway.py` exercises the complete SDLC pipeline to guard against regressions.

---

## Support & Community

**Questions, ideas, or integrations?**

- 📚 **[docs/configuration.md](docs/configuration.md)** — Configuration reference
- 🛠️ **Open an Issue** — Report bugs or request features
- 💬 **[TraceFox Slack](https://tracefox-community.slack.com)** — Join the community
- ✉️ **[hello@tracefox.ai](mailto:hello@tracefox.ai)** — Partnerships, pilots, or investor inquiries

---

## Tech Stack

**Backend**
- FastAPI, Pydantic, SQLAlchemy
- PostgreSQL, Redis, Neo4j, Qdrant
- Observability: OpenTelemetry, Prometheus

**Frontend**
- Next.js 14+, React, TypeScript
- SWR for data fetching, Tailwind CSS for styling
- Toast notifications, Skeleton loading

**Infrastructure**
- Docker & Docker Compose for local dev
- Terraform for cloud deployment
- GitHub Actions for CI/CD

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Let's ship resilient software together.** 🦊✨

Built with ❤️ by the TraceFox team

</div>
