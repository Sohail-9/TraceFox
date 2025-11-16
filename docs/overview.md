# TraceFox Low-Level Design (LLD)

TraceFox is an AI-powered code review platform that combines graph-backed code intelligence, a multi-tier LLM routing strategy, and strict confidence scoring to deliver production-grade reviews in under 60 seconds with <5% false positives. This document condenses the authoritative LLD into an implementation guide for the repository.

## 1. System Architecture Overview

### 1.1 Component Layers
```
┌────────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER                                          │
│ GitHub/GitLab Apps · Mission Control UI · CLI · Alerts      │
└────────────────────────────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────┐
│ API GATEWAY LAYER                                           │
│ Request routing · AuthN/Z · Rate limiting · Response cache  │
└────────────────────────────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────┐
│ SERVICE LAYER                                               │
│ Code Indexing · PR Analysis · Confidence Scoring            │
│ Learning & Feedback · Query Orchestration                   │
└────────────────────────────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────┐
│ LLM INFERENCE LAYER & UTILITIES                             │
│ services/shared/llm_utils.py (central provider hub)         │
│ DeepSeek via Ola Krutrim · Local Llama                      │
└────────────────────────────────────────────────────────────┘
↓
┌────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                  │
│ Neo4j (graph) · PostgreSQL (relational) · Redis (cache)     │
│ RabbitMQ/Kafka (events)                                     │
└────────────────────────────────────────────────────────────┘
```

### 1.2 Three-Tier Model Strategy
| Tier | Model | Purpose | Notes |
|------|-------|---------|-------|
| 1 | DeepSeek-R1 via Ola Krutrim | Complex reasoning, breaking-change detection, performance/security flows | Endpoint `https://cloud.olakrutrim.com/v1`, pay-per-request |
| 2 | Llama 2/3 (provider/local) | Detailed pattern detection, security validation, style and consistency checks | Runs after quick filter flags potential issues |
| 3 | Llama 3 8B (local) | Fast pre-screening of PRs, trivial change detection, syntax checks | <2s latency target |

### 1.3 Key Design Principles
- Precision-first: enforce <5% false-positive rate and suppress low-confidence findings.
- Provider abstraction: all LLM integrations flow through `services/shared/llm_utils.py`.
- Cost optimization: waterfall from free/fast local Llama to paid Ola Krutrim only when needed.
- Incremental indexing: re-index only changed files and dependent graph nodes.
- Modular microservices: hardened contracts between API gateway and service layer.
- Event-driven: message queues for asynchronous orchestration and retries.
- Feedback-driven learning: developer responses feed back into scoring models.

## 2. LLM Strategy & Integration

### 2.1 `services/shared/llm_utils.py`: Centralized Provider Management
**Purpose**: unify provider metadata, pricing, token accounting, and payload construction.

```python
MODEL_REGISTRY = {
    "deepseek-r1": ProviderMetadata(
        provider_key="ola_krutrim",
        model_name="DeepSeek-R1",
        default_endpoint="https://cloud.olakrutrim.com/v1",
        completion_path="/chat/completions",
        supports_structured_content=True,
        supports_stream=True,
    ),
    "gemma-3-27b-it": ProviderMetadata(
        provider_key="ola_krutrim",
        model_name="Gemma-3-27B-IT",
        default_endpoint="https://cloud.olakrutrim.com/v1",
        completion_path="/chat/completions",
        supports_structured_content=False,
        supports_stream=False,
    ),
}
```

**Core helpers**:
- `get_llm_context(model)` → resolves provider config, API keys, headers, and capability flags.
- `calculate_cost(model, prompt_tokens, completion_tokens)` → USD cost based on registry pricing.
- `prepare_llm_payload(model, messages, **extra)` → respects streaming & structured-content support.
- `call_chat_completion(model, messages, **kwargs)` → HTTP POST with retry logic, circuit breaker, and usage parsing.
- `count_tokens_in_messages(messages, model)` → uses `tiktoken` if installed, otherwise heuristic.
- `get_model_capabilities`, `supports_function_calling`, `supports_stream_options` → gating logic for routing.

**Pricing (per 100K tokens)**:
- DeepSeek-R1: input $0.084942 (cache $0.042471), output $0.34749.
- Gemma-3-27B-IT: input $0.061776 (cache $0.030888), output $0.19305.

**Configuration resolution**:
```python
def resolve_provider_config(provider_key: str) -> Mapping[str, Any]:
    settings = get_settings()
    provider_config = settings.ai_models.providers.get(provider_key, {})
    return {
        "endpoint": provider_config.get("endpoint") or MODEL_REGISTRY[provider_key].default_endpoint,
        "api_key": provider_config.get("api_key")
            or os.getenv(provider_config.get("api_key_env", ""))
            or os.getenv("TRACEFOX_OLA_KRUTRIM_API_KEY"),
        "timeout": provider_config.get("timeout", 30),
    }
```

Environment priority: 1) explicit config `api_key`, 2) `api_key_env`, 3) `TRACEFOX_OLA_KRUTRIM_API_KEY`.

### 2.2 Ola Krutrim Provider Integration
- **Endpoint**: `https://cloud.olakrutrim.com/v1` (`/chat/completions`).
- **Auth**: Bearer token via `Authorization: Bearer <api_key>`.
- **Request payload**:
```json
{
  "model": "DeepSeek-R1",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "temperature": 0.1,
  "top_p": 0.9,
  "max_tokens": 4096,
  "stream": false
}
```
- **Response**: OpenAI-style `chat.completion` object with `usage.prompt_tokens`, `usage.completion_tokens`, etc. Parsed centrally for billing + observability.

### 2.3 Llama Model Integration
- **Deployment**: local inference (Ollama/vLLM) at `http://localhost:11434`.
- **Models**:
  - Llama 3 70B → deep pattern + security analysis.
  - Llama 3 8B → fast filtering and syntax gate.
- **Request**:
```json
{
  "model": "llama3",
  "prompt": "...",
  "stream": false,
  "temperature": 0.1,
  "num_predict": 512
}
```
- **Cost**: zero per request after model download; only hardware costs.

## 3. Core Microservices

### 3.1 Code Indexing Service (`services/code_indexing/service.py`)
- **Responsibilities**: parse repos, build Code Property Graph (CPG), populate Neo4j + PostgreSQL metadata, and expose `/api/v1/index/*` endpoints.
- **Tech stack**: Tree-sitter parsing, Neo4j graph storage, PostgreSQL relational metadata, Redis caching for dedupe.
- **Graph schema**:
  - Nodes: `File`, `Function`, `Class`, `Variable`, `Import`.
  - Relationships: `CONTAINS`, `CALLS`, `IMPORTS`, `EXTENDS`, `USES`, `DEPENDS_ON`.
- **PostgreSQL tables**:
```sql
CREATE TABLE indexed_files (
  id UUID PRIMARY KEY,
  repository VARCHAR(255) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  file_hash VARCHAR(64),
  language VARCHAR(50),
  last_indexed_at TIMESTAMP,
  UNIQUE(repository, file_path)
);
CREATE TABLE code_elements (
  id UUID PRIMARY KEY,
  file_id UUID REFERENCES indexed_files(id),
  element_type VARCHAR(50),
  element_name VARCHAR(255),
  line_start INT,
  line_end INT,
  complexity INT,
  created_at TIMESTAMP
);
```
- **APIs**:
  - `POST /api/v1/index/repository` → clones repo, indexes branch.
  - `POST /api/v1/index/files` → accepts specific file payloads for incremental updates.

### 3.2 PR Analysis Engine (`services/review_engine/service.py`)
- **Flow**:
  1. GitHub webhook triggers ingestion (diff + metadata).
  2. Llama 3 8B quick filter (syntax/trivial detection).
  3. Parallel analysis: security/style (Llama 70B), complex logic (DeepSeek via Ola Krutrim), and cross-file reasoning (Neo4j queries).
  4. Ensemble confidence scoring and threshold filtering.
  5. Persistence + GitHub comments/notifications.
- **Pseudo-code**:
```python
class PRAnalysisEngine:
    async def analyze_pr(self, repo: str, pr_number: int) -> list[Finding]:
        pr_diff = self.fetch_pr_diff(repo, pr_number)
        changed_files = self.extract_changed_files(pr_diff)
        if not self.has_issues_quick_filter(pr_diff):
            return []
        security = await analyze_security_and_style(pr_diff)  # Llama
        context = self.build_analysis_context(changed_files)
        complex_logic = await analyze_complex_logic(pr_diff, context, model="deepseek-r1")
        cross_file = await analyze_cross_file_impact(changed_files)
        scored = self.score_findings(security + complex_logic + cross_file)
        return [f for f in scored if f.confidence >= 0.50]
```

### 3.3 Confidence Scoring Service (`services/scoring/service.py`)
- **Algorithm**: ensemble of four sub-models (pattern deviation 40%, context relevance 30%, historical accuracy 20%, cross-validation 10%) followed by model multiplier derived from true-positive rates.
- **Thresholds**:
  - `MUST_FIX` ≥ 0.90 (critical, red)
  - `SHOULD_FIX` ≥ 0.70 (important, yellow)
  - `NICE_TO_FIX` ≥ 0.50 (suggestion, blue)
  - `< 0.50` suppressed

### 3.4 Query Orchestration Service (`services/query/service.py`)
- **Purpose**: optimized data retrieval across Neo4j, PostgreSQL, and Redis caches.
- **Example**:
```python
def query_function_impact(self, function_id: str, max_depth: int = 3) -> dict:
    cache_key = f"function_impact:{function_id}"
    if cached := self.cache.get(cache_key):
        return json.loads(cached)
    result = self.graph_db.query(
        "MATCH (f:Function {id:$id}) "
        "CALL apoc.path.subgraphAll(f, {relationshipFilter:'CALLS', maxLevel:$depth}) "
        "YIELD nodes, relationships RETURN nodes, relationships",
        {"id": function_id, "depth": max_depth},
    )
    self.cache.setex(cache_key, 3600, json.dumps(result))
    return result
```

## 4. Data Layer Schemas

### 4.1 Neo4j Graph
- **Constraints/Indexes**:
  - `CREATE CONSTRAINT unique_file_path ON (f:File) ASSERT f.path IS UNIQUE;`
  - `CREATE CONSTRAINT unique_function_sig ON (fn:Function) ASSERT fn.signature IS UNIQUE;`
  - `CREATE INDEX idx_file_language ON :File(language);`
  - `CREATE INDEX idx_function_complexity ON :Function(complexity);`
  - `CREATE INDEX idx_function_name ON :Function(name);`
- **Nodes**:
  - `File`: `{id, path, language, hash, last_indexed_at}`
  - `Function`: `{id, name, signature, complexity, line_start, line_end, is_exported}`
  - `Class`: `{id, name, line_start, line_end}`
- **Relationships**: `CONTAINS`, `CALLS`, `IMPORTS`, `EXTENDS`, `DEPENDS_ON` (file-file), with enriched properties (line numbers, async flags, etc.).

### 4.2 PostgreSQL (PR Analysis + Feedback)
```sql
CREATE TABLE pr_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repository VARCHAR(255) NOT NULL,
  pr_number INT NOT NULL,
  pr_title TEXT,
  analysis_status VARCHAR(50),
  primary_model VARCHAR(50),
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  duration_ms INT,
  findings_count INT,
  UNIQUE(repository, pr_number)
);
CREATE TABLE findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pr_analysis_id UUID REFERENCES pr_analyses(id) ON DELETE CASCADE,
  finding_type VARCHAR(100),
  severity VARCHAR(50),
  confidence DECIMAL(3,2),
  source_model VARCHAR(50),
  message TEXT,
  file_path VARCHAR(255),
  line_number INT,
  suggested_fix TEXT,
  status VARCHAR(50) DEFAULT 'open'
);
CREATE TABLE feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
  feedback_type VARCHAR(50),
  developer_id VARCHAR(255),
  feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE model_performance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name VARCHAR(100),
  date DATE,
  true_positives INT,
  false_positives INT,
  false_negatives INT,
  precision DECIMAL(5,4),
  recall DECIMAL(5,4),
  f1_score DECIMAL(5,4)
);
CREATE INDEX idx_pr_repo ON pr_analyses(repository);
CREATE INDEX idx_findings_pr ON findings(pr_analysis_id);
CREATE INDEX idx_findings_model ON findings(source_model);
```

## 5. API Gateway & Request Flow

### 5.1 Model Routing Rules
```python
class ModelRouter:
    routing_rules = {
        "quick_filter": {"model": "llama", "version": "3-8b", "reason": "Fast pre-screening"},
        "security": {"model": "llama", "version": "2-70b", "reason": "Security pattern matching"},
        "breaking_changes": {"model": "deepseek", "reason": "Complex reasoning"},
        "performance": {"model": "deepseek", "reason": "Optimization analysis"},
        "cross_layer": {"model": "deepseek", "reason": "Multi-system reasoning"},
    }
```

### 5.2 Request Flow
1. **GitHub webhook** → verify signature, persist PR metadata.
2. **Quick filter** (Llama 3 8B) → <2s gate; trivial PRs exit early.
3. **Context fetch** → Neo4j graph neighbors, changed files, related code.
4. **Parallel analysis** → Llama security/style, DeepSeek complex logic, Neo4j cross-file queries.
5. **Confidence scoring** → ensemble + suppression thresholds.
6. **Results publishing** → PostgreSQL storage, GitHub comments, Slack/email/CLI updates.
7. **Feedback collection** → capture developer actions, update model metrics.

### 5.3 API Contracts
- `POST /api/v1/analyze/pr`
```json
{
  "repository": "owner/repo",
  "pr_number": 42,
  "changed_files": ["src/auth.ts"],
  "diff": "..."
}
```
- **Response**:
```json
{
  "pr_id": "owner/repo#42",
  "findings": [
    {
      "type": "security",
      "severity": "high",
      "confidence": 0.92,
      "message": "Hardcoded password",
      "source_model": "llama"
    }
  ]
}
```
- Additional endpoints: `GET /api/v1/analysis/{analysis_id}`, `POST /api/v1/feedback/{finding_id}`.

## 6. Data Models
```python
class FindingType(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    LOGIC = "logic"
    BREAKING_CHANGE = "breaking_change"
    CROSS_LAYER = "cross_layer"

class FindingSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Finding:
    type: FindingType
    severity: FindingSeverity
    confidence: float
    message: str
    file_path: str
    line_number: int
    suggested_fix: Optional[str] = None
    source_model: str = "unknown"

@dataclass
class PRAnalysis:
    pr_id: str
    repository: str
    pr_number: int
    findings: list[Finding]
    duration_ms: int
    primary_model: str
    analysis_status: str
```

## 7. Error Handling & Resilience

### 7.1 Circuit Breakers
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.state = "CLOSED"
        ...

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception:
            self.on_failure()
            raise
```

### 7.2 Retry Strategy
```python
def retry_with_backoff(func, max_retries: int = 3, base_delay: int = 1):
    for attempt in range(max_retries):
        try:
            return func()
        except (TimeoutError, ConnectionError) as exc:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), 60)
            logger.warning("Retry %s/%s after %ss: %s", attempt + 1, max_retries, delay, exc)
            time.sleep(delay)
```

### 7.3 Service Timeouts
- PR analysis total 60s (quick filter 2s, security analysis 10s, DeepSeek pass 15s, confidence scoring 5s).
- Graph queries: 2s simple lookups, 15s complex traversals.
- Llama inference: 30s; Ola Krutrim inference: 20s.

## 8. Monitoring & Observability

### 8.1 Metrics
- Quality: PR latency (p50/p95/p99), false-positive rate by type, model accuracy comparison, developer acceptance rate, confidence calibration.
- Cost: Ola Krutrim spend per analysis, tokens per request, trend over time.
- System: cache hit rate, API latency, service uptime, error rates, DB latency, queue depth.

### 8.2 Logging
```python
logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(handler)
logger.info(
    "PR analysis started",
    extra={"pr_id": "owner/repo#42", "model": "llama", "duration_ms": 5000},
)
```

## 9. Security Considerations

- **AuthN/Z**: OAuth2 + JWT (providers: GitHub, GitLab). Issuer `https://auth.tracefox.io`, token TTL 24h, refresh 7d.
- **Roles**:
  - `admin`: full access.
  - `reviewer`: read/dismiss findings.
  - `developer`: read findings on owned PRs.
- **API keys**: Ola Krutrim keys pulled from env vars, rotated regularly, validated at startup.
- **Data security**: TLS for all APIs, SSL DB connections, OAuth tokens never persisted, secrets stored outside code, analysis results persisted in PostgreSQL only.

## 10. Cost Estimation
- Ola Krutrim (DeepSeek): ~$0.00036 per PR (example: 2k input + 500 output tokens @ $0.14/$0.42 per 1M).
- 10k PRs/month ≈ $3.60.
- Llama local inference: free per-request after download; hardware amortized across services.

## 11. Implementation Phases
| Phase | Duration | Objectives |
|-------|----------|------------|
| 1 | Weeks 1-2 | Stand up PostgreSQL + Neo4j, implement code indexing & graph schema |
| 2 | Weeks 3-4 | Integrate Llama stack, configure Ola Krutrim provider, ship `llm_utils.py` |
| 3 | Weeks 5-6 | Build PR analysis engine, implement multi-pass analysis & routing |
| 4 | Weeks 7-8 | Deliver confidence scoring, GitHub integration, result publishing |
| 5 | Weeks 9-10 | Performance hardening, end-to-end testing, feedback ingestion |

## 12. Success Criteria
- **Technical KPIs**: false-positive rate <5%, PR latency p95 <60s, uptime >99%, accuracy (Llama ≥85%, DeepSeek ≥90%).
- **Business KPIs**: >80% developer adoption, ≥70% finding acceptance, <$0.01 per analysis, customer satisfaction ≥4/5.

## Conclusion
TraceFox’s production blueprint hinges on centralized LLM provider governance, a cost-aware three-tier model stack, resilient microservices, and continuous feedback loops. The design here maps directly to the repository: keep all LLM interactions inside `services/shared/llm_utils.py`, feed combined findings through the scoring service, leverage Neo4j/PostgreSQL/Redis for context, and enforce the monitoring + security practices outlined above. This alignment ensures the implementation stays precise, scalable, and economical as providers and workloads evolve.
