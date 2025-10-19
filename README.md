TraceFox is an AI-powered platform that automates the entire software development lifecycle. It offers unified code analysis, intelligent test generation, simulated execution, root cause analysis, and actionable notifications so engineering teams can trace issues from commits to production outcomes.

This repository now includes a lightweight proof-of-concept that mirrors the architecture described in the TraceFox technical design document. The MVP focuses on a single commit-oriented workflow that stitches together the core AI-powered touchpoints.

## What the MVP Demonstrates
- Code analysis over supplied file changes with simple AST heuristics and risk scoring.
- Heuristic test generation that prioritises cases based on perceived risk.
- Simulated test execution with deterministic pass/fail outcomes.
- Root cause analysis using a tiny in-memory knowledge base.
- Notification formatting that could be bridged to Slack/Email channels.
- A FastAPI endpoint (`POST /demo/run`) that orchestrates the entire lifecycle.

## Getting Started
1. Create and activate a Python 3.10+ virtual environment.
2. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the API locally:
   ```bash
   uvicorn services.api_gateway.main:app --reload
   ```

## Example Request
Send a commit payload to trigger the end-to-end workflow:

```bash
curl -X POST http://localhost:8000/demo/run \
  -H "Content-Type: application/json" \
  -d '{
        "commit_id": "abc1234",
        "files": [
          {
            "path": "app/main.py",
            "content": "def add(a, b):\n    return a + b\n"
          }
        ]
      }'
```

The response includes:
- `code_analysis`: AST-based metrics and risk scoring.
- `test_generation`: Suggested tests with P0/P1/P2 priorities.
- `test_execution`: Simulated run results with short logs.
- `debugging`: Root cause hypotheses that point to similar past incidents.
- `notification`: Pre-formatted summary ready for downstream channels.

## Next Steps
- Replace heuristics with actual model calls (CodeLlama, GPT-4, Krutrim).
- Externalise state into databases, queues, and vector stores.
- Expand coverage for additional languages, frameworks, and CI signals.
- Enrich notifications with links to dashboards, incidents, and RCA threads.
