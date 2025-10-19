## DevGuardian End-to-End Walkthrough

The proof-of-concept mirrors the ten-step workflow described in the DevGuardian technical documentation. Each microservice is represented with FastAPI-friendly Python modules so the orchestration can be exercised locally without external infrastructure.

### Workflow Highlights
1. **Event Processing Service**  
   - Accepts webhook-style commit and deployment payloads.  
   - Normalises timestamps, authors, and repositories before invoking the orchestrator.
2. **User Management Service**  
   - Resolves plan tier, locale, and feature flags.  
   - Drives model routing (e.g., Krutrim for Indic locales) and monitoring entitlements.
3. **Code Analysis Service**  
   - Parses Python code to produce AST counts, risk scores, and mock embedding identifiers.  
   - Prefers the Krutrim DeepSeek R1 base model and escalates to CodeLlama for large or non-Python files.  
   - Demonstrates response caching with in-memory hit tracking.
4. **Test Generation Service**  
   - Prioritises test cases by risk.  
   - Chooses appropriate models (GPT-4, Claude, Llama 3.1, Krutrim) based on risk and locale, defaulting to Krutrim DeepSeek R1.  
   - Emits confidence estimates and actionable assertion prompts.
5. **Test Execution Service**  
   - Simulates deterministic execution durations and pass/fail states.  
   - Marks high-priority regressions for retry to highlight escalation paths.
6. **Debugging Service + Knowledge Base**  
   - Performs RCA on failing tests using keyword-based retrieval from a seeded incident corpus.  
   - Routes high-severity issues to GPT-4 or Krutrim, mirroring the real hybrid strategy.
7. **Production Monitor Service**  
   - Inspects deployment metrics (latency, error rate, CPU) and raises alerts when deviations exceed baselines.  
   - Labels anomalies with the heuristic equivalent of Isolation Forest scoring.
8. **Notification Service**  
   - Generates Slack/email-ready summaries that unify commit outcomes and production anomalies.  
   - Injects severity levels to mimic channel-specific routing.
9. **Analytics Service**  
   - Creates a consolidated report combining test failures, RCA output, and production alerts.  
   - Provides insights suitable for dashboards, QBRs, or SLA reviews.
10. **Agent Orchestrator**  
    - Bridges all services, keeps the latest analytics report in memory, and exposes helper methods for API and CLI callers.

### Extensibility Hooks
- Swap heuristic components for real model clients using the same method signatures.
- Replace in-memory caches with Redis and vector DB stubs with Pinecone or Weaviate connectors.
- Persist analytics, incidents, and metrics in PostgreSQL/TimescaleDB to drive longitudinal reporting.
- Add API authentication, rate limiting, and multi-tenant routing in the API Gateway.

### Running the Scenario
1. Start the API with `uvicorn services.api_gateway.main:app --reload`.
2. POST a commit payload to `/events/commit` to trigger the development lifecycle.
3. POST a deployment payload to `/events/deployment` to simulate production monitoring.
4. Query `/analytics/latest` for a consolidated report after either event.

Alternatively, execute `python3 scripts/run_demo.py` to step through the full flow without running the server.

### Deploying the Demo
- Use `Dockerfile` + `scripts/build_image.sh` to publish a container image.
- Apply the Terraform in `infrastructure/aws` for ECS Fargate or `infrastructure/azure` for Azure Container Apps. Both templates wire in the Krutrim/DeepSeek defaults and expose outputs for downstream automation.
