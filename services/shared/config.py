"""Centralised configuration management for TraceFox services.

This module intentionally avoids hard-coded configuration values. All
operational parameters are sourced from environment variables or an optional
external configuration document referenced by ``TRACEFOX_CONFIG_FILE``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple, TypeVar

try:  # Python 3.11+ ships tomllib by default
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for alternative runtimes
    tomllib = None  # type: ignore

try:  # Optional dependency - only needed when YAML configuration is in use
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - YAML support is optional
    yaml = None  # type: ignore

T = TypeVar("T")


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class ConfigProvider:
    """Resolve configuration values from environment variables and config files."""

    def __init__(
        self,
        *,
        env_prefix: str = "TRACEFOX_",
        file_env_var: str = "TRACEFOX_CONFIG_FILE",
    ) -> None:
        self._env_prefix = env_prefix
        self._file_env_var = file_env_var
        self._lock = RLock()
        self._cache: Dict[str, Any] = {}
        self._load_env_file()
        self._file_data = self._load_file_data()

    def _load_env_file(self) -> None:
        """Populate os.environ from an optional .env file before resolving config."""

        # Allow overriding the env file location via TRACEFOX_ENV_FILE. Empty value disables loading.
        env_file_hint = os.getenv(f"{self._env_prefix}ENV_FILE", ".env")
        if not env_file_hint:
            return

        candidate_paths = []
        path_hint = Path(env_file_hint)
        if path_hint.is_absolute():
            candidate_paths.append(path_hint)
        else:
            candidate_paths.append(Path.cwd() / path_hint)
            # Fallback to repository root relative to this module (../.. from services/shared).
            candidate_paths.append(Path(__file__).resolve().parents[2] / path_hint)

        env_path = next((p for p in candidate_paths if p.exists()), None)
        if env_path is None:
            return

        try:
            with env_path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("export "):
                        line = line[len("export ") :].strip()
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if not key or key in os.environ:
                        continue
                    value = value.strip()
                    if (
                        len(value) >= 2
                        and value[0] == value[-1]
                        and value[0] in {'"', "'"}
                    ):
                        value = value[1:-1]
                    os.environ[key] = value
        except OSError as exc:  # pragma: no cover - defensive
            raise ConfigurationError(f"Unable to read environment file {env_path}") from exc

    def _load_file_data(self) -> Mapping[str, Any]:
        file_path_value = os.getenv(self._file_env_var)
        if not file_path_value:
            return {}

        path = Path(file_path_value)
        if not path.exists():
            raise ConfigurationError(f"Configuration file {path} not found")

        suffix = path.suffix.lower()
        if suffix in {".json", ".jsonc"}:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        elif suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise ConfigurationError(
                    "PyYAML is required to read YAML configuration but is not installed"
                )
            with path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)  # type: ignore[union-attr]
            data = loaded or {}
        elif suffix in {".toml", ".tml"}:
            if tomllib is None:  # pragma: no cover - unexpected for Python 3.11+
                raise ConfigurationError("tomllib is unavailable on this interpreter")
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        else:
            raise ConfigurationError(
                f"Unsupported configuration format '{suffix}'. "
                "Use JSON, YAML, or TOML."
            )

        if not isinstance(data, Mapping):
            raise ConfigurationError("Configuration document root must be a mapping")
        return data

    def _normalise_key(self, key: str) -> str:
        return key.replace("__", ".").strip()

    def _env_key(self, key: str) -> str:
        return f"{self._env_prefix}{self._normalise_key(key).upper().replace('.', '__')}"

    def _lookup_file_value(self, key: str) -> Any:
        current: Any = self._file_data
        if not key:
            return current
        for part in self._normalise_key(key).split("."):
            if not isinstance(current, Mapping) or part not in current:
                return None
            current = current[part]
        return current

    def _from_env(self, key: str) -> Optional[str]:
        return os.getenv(self._env_key(key))

    def _apply_cast(self, raw: Any, cast: Optional[Callable[[Any], T]]) -> T:
        if cast is None:
            return raw  # type: ignore[return-value]
        try:
            return cast(raw)
        except Exception as exc:  # pragma: no cover - defensive
            raise ConfigurationError(f"Unable to cast value '{raw}' using {cast}") from exc

    def _cache_key(self, key: str) -> str:
        return self._normalise_key(key)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def get(
        self,
        key: str,
        *,
        default: Any = None,
        cast: Optional[Callable[[Any], T]] = None,
        required: bool = False,
    ) -> T:
        cache_key = self._cache_key(key)
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

            raw: Any = self._from_env(key)
            if raw is None:
                raw = self._lookup_file_value(key)

            if raw is None:
                if required:
                    raise ConfigurationError(f"Missing configuration value for '{key}'")
                value = default
            else:
                value = self._apply_cast(raw, cast)

            self._cache[cache_key] = value
            return value

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        raise ConfigurationError(f"Unable to coerce value '{value}' to boolean")

    @staticmethod
    def _coerce_int(value: Any) -> int:
        if isinstance(value, bool):  # pragma: no cover - defensive
            raise ConfigurationError("Boolean cannot be coerced to integer")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value.strip())
        raise ConfigurationError(f"Unable to coerce value '{value}' to integer")

    @staticmethod
    def _coerce_float(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        raise ConfigurationError(f"Unable to coerce value '{value}' to float")

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        return str(value)

    def get_bool(self, key: str, *, default: Optional[bool] = None) -> Optional[bool]:
        return self.get(key, default=default, cast=self._coerce_bool)

    def require_bool(self, key: str) -> bool:
        return self.get(key, cast=self._coerce_bool, required=True)

    def get_int(self, key: str, *, default: Optional[int] = None) -> Optional[int]:
        return self.get(key, default=default, cast=self._coerce_int)

    def require_int(self, key: str) -> int:
        return self.get(key, cast=self._coerce_int, required=True)

    def get_float(self, key: str, *, default: Optional[float] = None) -> Optional[float]:
        return self.get(key, default=default, cast=self._coerce_float)

    def require_float(self, key: str) -> float:
        return self.get(key, cast=self._coerce_float, required=True)

    def get_str(self, key: str, *, default: Optional[str] = None) -> Optional[str]:
        value = self.get(key, default=default, cast=self._coerce_str)
        return value

    def require_str(self, key: str) -> str:
        return self.get(key, cast=self._coerce_str, required=True)

    def get_sequence(self, key: str) -> Sequence[Any]:
        raw = self.get(key)
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            return list(raw)
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise ConfigurationError(f"Invalid JSON list for '{key}'") from exc
                if not isinstance(parsed, list):
                    raise ConfigurationError(f"Configuration value for '{key}' must be a list")
                return parsed
            return [item.strip() for item in text.split(",") if item.strip()]
        raise ConfigurationError(f"Configuration value for '{key}' must be a sequence")

    def get_mapping(self, key: str) -> Mapping[str, Any]:
        raw = self.get(key)
        if raw is None:
            return {}
        if isinstance(raw, Mapping):
            return raw
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ConfigurationError(f"Invalid JSON mapping for '{key}'") from exc
            if not isinstance(parsed, Mapping):
                raise ConfigurationError(f"Configuration value for '{key}' must be a mapping")
            return parsed
        raise ConfigurationError(f"Configuration value for '{key}' must be a mapping")


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    min_pool: int
    max_pool: int
    connection_timeout_seconds: float
    statement_timeout_seconds: float
    max_idle_seconds: float

    @classmethod
    def load(cls, provider: ConfigProvider) -> "DatabaseSettings":
        return cls(
            host=provider.require_str("postgres.host"),
            port=provider.require_int("postgres.port"),
            user=provider.require_str("postgres.user"),
            password=provider.require_str("postgres.password"),
            database=provider.require_str("postgres.database"),
            min_pool=provider.require_int("postgres.min_pool"),
            max_pool=provider.require_int("postgres.max_pool"),
            connection_timeout_seconds=provider.require_float("postgres.connection_timeout_seconds"),
            statement_timeout_seconds=provider.require_float("postgres.statement_timeout_seconds"),
            max_idle_seconds=provider.require_float("postgres.max_idle_seconds"),
        )


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    db: int
    max_connections: int
    socket_timeout_seconds: float
    key_version: str
    default_ttl_seconds: int

    @classmethod
    def load(cls, provider: ConfigProvider) -> "RedisSettings":
        return cls(
            host=provider.require_str("redis.host"),
            port=provider.require_int("redis.port"),
            username=provider.get_str("redis.username"),
            password=provider.get_str("redis.password"),
            db=provider.require_int("redis.db"),
            max_connections=provider.require_int("redis.max_connections"),
            socket_timeout_seconds=provider.require_float("redis.socket_timeout_seconds"),
            key_version=provider.require_str("redis.key_version"),
            default_ttl_seconds=provider.require_int("redis.default_ttl_seconds"),
        )


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str
    max_connection_pool_size: int
    acquisition_timeout_seconds: float
    encrypted: bool

    @classmethod
    def load(cls, provider: ConfigProvider) -> "Neo4jSettings":
        return cls(
            uri=provider.require_str("neo4j.uri"),
            user=provider.require_str("neo4j.user"),
            password=provider.require_str("neo4j.password"),
            max_connection_pool_size=provider.require_int("neo4j.max_connection_pool_size"),
            acquisition_timeout_seconds=provider.require_float(
                "neo4j.connection_acquisition_timeout_seconds"
            ),
            encrypted=provider.require_bool("neo4j.encrypted"),
        )


@dataclass(frozen=True)
class StorageSettings:
    provider: str
    bucket: str
    region: Optional[str]
    kms_key_id: Optional[str]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "StorageSettings":
        return cls(
            provider=provider.require_str("storage.provider"),
            bucket=provider.require_str("storage.bucket"),
            region=provider.get_str("storage.region"),
            kms_key_id=provider.get_str("storage.kms_key_id"),
        )


@dataclass(frozen=True)
class ObservabilitySettings:
    traces_endpoint: Optional[str]
    metrics_endpoint: Optional[str]
    logs_endpoint: Optional[str]
    sampling_ratio: float
    exporter_protocol: Optional[str]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "ObservabilitySettings":
        return cls(
            traces_endpoint=provider.get_str("observability.traces_endpoint"),
            metrics_endpoint=provider.get_str("observability.metrics_endpoint"),
            logs_endpoint=provider.get_str("observability.logs_endpoint"),
            sampling_ratio=provider.require_float("observability.sampling_ratio"),
            exporter_protocol=provider.get_str("observability.exporter_protocol"),
        )


@dataclass(frozen=True)
class MessagingSettings:
    broker_url: str
    consumer_groups: Sequence[str]
    queue_max_size: int
    delivery_timeout_seconds: float
    management_url: Optional[str]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "MessagingSettings":
        return cls(
            broker_url=provider.require_str("messaging.broker_url"),
            consumer_groups=provider.get_sequence("messaging.consumer_groups"),
            queue_max_size=provider.require_int("messaging.queue_max_size"),
            delivery_timeout_seconds=provider.require_float(
                "messaging.delivery_timeout_seconds"
            ),
            management_url=provider.get_str("messaging.management_url"),
        )


@dataclass(frozen=True)
class RetryPolicySettings:
    enabled: bool
    initial_interval_seconds: float
    multiplier: float
    max_interval_seconds: float
    max_elapsed_time_seconds: float
    randomization_factor: float
    max_retries: int

    @classmethod
    def load(cls, provider: ConfigProvider) -> "RetryPolicySettings":
        return cls(
            enabled=provider.require_bool("retry.enabled"),
            initial_interval_seconds=provider.require_float("retry.initial_interval_seconds"),
            multiplier=provider.require_float("retry.multiplier"),
            max_interval_seconds=provider.require_float("retry.max_interval_seconds"),
            max_elapsed_time_seconds=provider.require_float("retry.max_elapsed_time_seconds"),
            randomization_factor=provider.require_float("retry.randomization_factor"),
            max_retries=provider.require_int("retry.max_retries"),
        )


@dataclass(frozen=True)
class CircuitBreakerSettings:
    failure_rate_threshold: float
    slow_call_rate_threshold: float
    slow_call_duration_threshold_seconds: float
    sliding_window_size: int
    minimum_number_of_calls: int
    wait_duration_in_open_state_seconds: float
    permitted_calls_in_half_open_state: int

    @classmethod
    def load(cls, provider: ConfigProvider) -> "CircuitBreakerSettings":
        return cls(
            failure_rate_threshold=provider.require_float("circuit_breaker.failure_rate_threshold"),
            slow_call_rate_threshold=provider.require_float(
                "circuit_breaker.slow_call_rate_threshold"
            ),
            slow_call_duration_threshold_seconds=provider.require_float(
                "circuit_breaker.slow_call_duration_threshold_seconds"
            ),
            sliding_window_size=provider.require_int("circuit_breaker.sliding_window_size"),
            minimum_number_of_calls=provider.require_int(
                "circuit_breaker.minimum_number_of_calls"
            ),
            wait_duration_in_open_state_seconds=provider.require_float(
                "circuit_breaker.wait_duration_in_open_state_seconds"
            ),
            permitted_calls_in_half_open_state=provider.require_int(
                "circuit_breaker.permitted_calls_in_half_open_state"
            ),
        )


@dataclass(frozen=True)
class CacheSettings:
    namespace: str
    version: str
    default_ttl_seconds: int

    @classmethod
    def load(cls, provider: ConfigProvider) -> "CacheSettings":
        return cls(
            namespace=provider.require_str("cache.namespace"),
            version=provider.require_str("cache.version"),
            default_ttl_seconds=provider.require_int("cache.default_ttl_seconds"),
        )


@dataclass(frozen=True)
class SecuritySettings:
    jwt_issuer: Optional[str]
    jwks_url: Optional[str]
    allowed_audiences: Sequence[str]
    enforce_mtls: bool
    audit_topic: Optional[str]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "SecuritySettings":
        return cls(
            jwt_issuer=provider.get_str("security.jwt_issuer"),
            jwks_url=provider.get_str("security.jwks_url"),
            allowed_audiences=provider.get_sequence("security.allowed_audiences"),
            enforce_mtls=provider.require_bool("security.enforce_mtls"),
            audit_topic=provider.get_str("security.audit_topic"),
        )


@dataclass(frozen=True)
class GitHubOAuthSettings:
    client_id: Optional[str]
    client_secret: Optional[str]
    redirect_uri: Optional[str]
    scope: Tuple[str, ...]
    allowed_organizations: Tuple[str, ...]
    allowed_users: Tuple[str, ...]
    api_base: str
    login_base: str
    dev_mode: bool
    dev_login: Optional[str]
    dev_user_id: Optional[str]
    dev_email: Optional[str]
    dev_name: Optional[str]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "GitHubOAuthSettings":
        scope_values = provider.get_sequence("auth.github.scope") or ["read:user", "user:email"]
        allowed_orgs = tuple(provider.get_sequence("auth.github.allowed_organizations"))
        allowed_users = tuple(provider.get_sequence("auth.github.allowed_users"))
        client_id = provider.get_str("auth.github.client_id")
        dev_mode = provider.get_bool("auth.github.dev_mode", default=False) or False
        return cls(
            client_id=client_id,
            client_secret=provider.get_str("auth.github.client_secret"),
            redirect_uri=provider.get_str("auth.github.redirect_uri"),
            scope=tuple(str(scope) for scope in scope_values),
            allowed_organizations=tuple(str(org) for org in allowed_orgs),
            allowed_users=tuple(str(user) for user in allowed_users),
            api_base=provider.get_str("auth.github.api_base") or "https://api.github.com",
            login_base=provider.get_str("auth.github.login_base")
            or "https://github.com/login/oauth",
            dev_mode=dev_mode,
            dev_login=provider.get_str("auth.github.dev_login"),
            dev_user_id=provider.get_str("auth.github.dev_user_id"),
            dev_email=provider.get_str("auth.github.dev_email"),
            dev_name=provider.get_str("auth.github.dev_name"),
        )

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


@dataclass(frozen=True)
class AuthSettings:
    session_secret: str
    session_ttl_seconds: int
    state_ttl_seconds: int
    github: GitHubOAuthSettings

    @classmethod
    def load(cls, provider: ConfigProvider) -> "AuthSettings":
        session_secret = provider.get_str("auth.session_secret") or "tracefox-dev-secret"
        session_ttl = provider.get_int("auth.session_ttl_seconds")
        if session_ttl is None:
            session_ttl = 3600
        state_ttl = provider.get_int("auth.state_ttl_seconds")
        if state_ttl is None:
            state_ttl = 300

        github_settings = GitHubOAuthSettings.load(provider)
        if not github_settings.dev_mode and not github_settings.is_configured():
            raise ConfigurationError(
                "GitHub OAuth is not fully configured. Provide client_id, client_secret, and redirect_uri "
                "or enable dev_mode for local testing."
            )

        return cls(
            session_secret=session_secret,
            session_ttl_seconds=int(session_ttl),
            state_ttl_seconds=int(state_ttl),
            github=github_settings,
        )


@dataclass(frozen=True)
class RateLimitSettings:
    global_rps: int
    burst: int
    per_tenant_rps: int

    @classmethod
    def load(cls, provider: ConfigProvider) -> "RateLimitSettings":
        return cls(
            global_rps=provider.require_int("rate_limit.global_rps"),
            burst=provider.require_int("rate_limit.burst"),
            per_tenant_rps=provider.require_int("rate_limit.per_tenant_rps"),
        )


@dataclass(frozen=True)
class AIModelSettings:
    default_temperature: float
    providers: Mapping[str, Mapping[str, Any]]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "AIModelSettings":
        return cls(
            default_temperature=provider.require_float("ai_models.default_temperature"),
            providers=provider.get_mapping("ai_models.providers"),
        )


@dataclass(frozen=True)
class QdrantCollectionSettings:
    name: str
    vector_size: int
    distance: str
    shard_number: Optional[int]
    on_disk_payload: bool

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "QdrantCollectionSettings":
        required_keys = {"name", "vector_size", "distance"}
        missing = required_keys - payload.keys()
        if missing:
            raise ConfigurationError(
                f"Qdrant collection configuration is missing required keys: {sorted(missing)}"
            )
        shard_number = payload.get("shard_number")
        return cls(
            name=str(payload["name"]),
            vector_size=int(payload["vector_size"]),
            distance=str(payload["distance"]),
            shard_number=int(shard_number) if shard_number is not None else None,
            on_disk_payload=bool(payload.get("on_disk_payload", True)),
        )


@dataclass(frozen=True)
class QdrantSettings:
    host: str
    port: int
    grpc_port: Optional[int]
    api_key: Optional[str]
    prefer_grpc: bool
    tls_enabled: bool
    replication_factor: int
    write_consistency_factor: int
    snapshot_schedule_cron: Optional[str]
    backup_storage_uri: Optional[str]
    backup_schedule_cron: Optional[str]
    collections: Tuple[QdrantCollectionSettings, ...]

    @classmethod
    def load(cls, provider: ConfigProvider) -> "QdrantSettings":
        collections_raw = provider.get_sequence("qdrant.collections")
        collections: Tuple[QdrantCollectionSettings, ...] = tuple(
            QdrantCollectionSettings.from_mapping(item)
            for item in collections_raw
            if isinstance(item, Mapping)
        )
        if len(collections) != len(collections_raw):
            raise ConfigurationError(
                "Each entry in 'qdrant.collections' must be a mapping object with the required keys"
            )

        return cls(
            host=provider.require_str("qdrant.host"),
            port=provider.require_int("qdrant.port"),
            grpc_port=provider.get_int("qdrant.grpc_port"),
            api_key=provider.get_str("qdrant.api_key"),
            prefer_grpc=provider.require_bool("qdrant.prefer_grpc"),
            tls_enabled=provider.require_bool("qdrant.tls_enabled"),
            replication_factor=provider.require_int("qdrant.replication_factor"),
            write_consistency_factor=provider.require_int("qdrant.write_consistency_factor"),
            snapshot_schedule_cron=provider.get_str("qdrant.snapshot_schedule_cron"),
            backup_storage_uri=provider.get_str("qdrant.backup_storage_uri"),
            backup_schedule_cron=provider.get_str("qdrant.backup_schedule_cron"),
            collections=collections,
        )


@dataclass(frozen=True)
class QualitySettings:
    flaky_threshold: float

    @classmethod
    def load(cls, provider: ConfigProvider) -> "QualitySettings":
        return cls(
            flaky_threshold=provider.require_float("quality.flaky_threshold"),
        )


@dataclass(frozen=True)
class Settings:
    environment: str
    api_gateway_host: str
    api_gateway_port: int
    api_gateway_allowed_origins: Sequence[str]
    postgres: DatabaseSettings
    redis: RedisSettings
    neo4j: Neo4jSettings
    storage: StorageSettings
    observability: ObservabilitySettings
    messaging: MessagingSettings
    retry: RetryPolicySettings
    circuit_breaker: CircuitBreakerSettings
    cache: CacheSettings
    security: SecuritySettings
    auth: AuthSettings
    rate_limit: RateLimitSettings
    ai_models: AIModelSettings
    qdrant: QdrantSettings
    quality: QualitySettings
    github: Any  # lightweight holder for optional GitHub settings

    @classmethod
    def load(cls, provider: Optional[ConfigProvider] = None) -> "Settings":
        source = provider or ConfigProvider()
        # GitHub integration (optional, keep flexible structure)
        github_settings = {
            "publish_enabled": source.get_bool("github.publish_enabled", default=False) or False,
            "api_base": source.get_str("github.api_base") or "https://api.github.com",
            "token": source.get_str("github.token"),
            "app_id": source.get_str("github.app_id"),
            "private_key_pem": source.get_str("github.private_key_pem"),
            "webhook_secret": source.get_str("github.webhook_secret"),
        }
        return cls(
            environment=source.require_str("environment"),
            api_gateway_host=source.require_str("api_gateway.host"),
            api_gateway_port=source.require_int("api_gateway.port"),
            api_gateway_allowed_origins=source.get_sequence("api_gateway.allowed_origins"),
            postgres=DatabaseSettings.load(source),
            redis=RedisSettings.load(source),
            neo4j=Neo4jSettings.load(source),
            storage=StorageSettings.load(source),
            observability=ObservabilitySettings.load(source),
            messaging=MessagingSettings.load(source),
            retry=RetryPolicySettings.load(source),
            circuit_breaker=CircuitBreakerSettings.load(source),
            cache=CacheSettings.load(source),
            security=SecuritySettings.load(source),
            auth=AuthSettings.load(source),
            rate_limit=RateLimitSettings.load(source),
            ai_models=AIModelSettings.load(source),
            qdrant=QdrantSettings.load(source),
            quality=QualitySettings.load(source),
            github=github_settings,
        )


@lru_cache(maxsize=1)
def get_settings(provider: Optional[ConfigProvider] = None) -> Settings:
    """Return cached settings loaded from environment or configuration service."""

    return Settings.load(provider)


def reload_settings() -> None:
    """Clear the settings cache to force a reload on next access."""

    get_settings.cache_clear()  # type: ignore[attr-defined]


__all__ = [
    "AIModelSettings",
    "CacheSettings",
    "CircuitBreakerSettings",
    "ConfigProvider",
    "ConfigurationError",
    "DatabaseSettings",
    "MessagingSettings",
    "Neo4jSettings",
    "ObservabilitySettings",
    "QdrantCollectionSettings",
    "QdrantSettings",
    "RateLimitSettings",
    "QualitySettings",
    "RedisSettings",
    "RetryPolicySettings",
    "SecuritySettings",
    "Settings",
    "StorageSettings",
    "get_settings",
    "reload_settings",
]
