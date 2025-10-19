# TraceFox Configuration Guide

TraceFox services read their operational settings from environment variables or a
configuration document referenced via the `TRACEFOX_CONFIG_FILE` environment
variable. No values are embedded in code, so a deployment must provide the full
configuration surface described below. A starter set of variables can be found
in `.env.example`; copy it to `.env` (or your secret store) and adjust per
environment.

## Loading order

1. If `TRACEFOX_CONFIG_FILE` is set, the file (JSON, YAML, or TOML) is parsed
   first. Supply your own managed document or configuration-service artifact.
2. Environment variables using the `TRACEFOX_` prefix override values from the
   configuration document. Nested keys are separated with `__`, e.g.
   `TRACEFOX_POSTGRES__HOST`. Compose stacks can provide these via `.env`
   injection.

All settings are cached in-process. Call `services.shared.config.reload_settings`
after rotating secrets or modifying runtime configuration.

## Required sections

| Section | Purpose |
| --- | --- |
| `environment`, `api_gateway` | Deployment metadata and ingress binding |
| `postgres`, `redis`, `neo4j` | Connection pooling, timeouts, and credentials |
| `storage` | Persistent object storage target (S3/GCS/etc.) |
| `observability` | OpenTelemetry endpoints and sampling ratios |
| `messaging` | Message broker location, consumer groups, backpressure limits |
| `retry`, `circuit_breaker` | Exponential backoff and breaker thresholds |
| `cache` | Namespace, semantic version, default TTL |
| `security` | AuthN/Z configuration, mTLS enforcement, audit topic |
| `rate_limit` | Global and per-tenant throttling |
| `ai_models` | Provider credentials and primary model selections |
| `qdrant` | Vector store cluster details, replication, backup cadences |
| `quality` | Quality gates such as flaky-test thresholds |

Missing fields raise a `ConfigurationError` at runtime.

## Versioned cache keys

`cache.namespace` and `cache.version` form the prefix for every cache key. When
schema changes require invalidation, bump `cache.version` instead of flushing
manually.

## Retry & circuit breaker tuning

`retry.*` drives exponential backoff (`initial_interval_seconds`, `multiplier`,
`max_interval_seconds`) plus jitter. `circuit_breaker.*` defines failure-rate
thresholds, slow-call detection, and the number of probes allowed while
half-open. These values affect all outbound operations wrapped via
`execute_with_resilience`.

## Qdrant durability & backups

`qdrant.collections` enumerates collections with vector size and distance
metrics. `replication_factor` and `write_consistency_factor` enforce data
redundancy. Snapshot and backup schedules (cron syntax) are used by the
shared vector manager to publish required backup jobs.

## Observability integration

Setting `observability.traces_endpoint` enables OTLP/GRPC exporting. When
absent, the system falls back to console spans, useful for local environments.
`observability.sampling_ratio` controls parent-based sampling.

---

Keep the example configuration file synced with infrastructure-as-code
defaults so new environments can bootstrap quickly.
