"""Centralised configuration for TraceFox services."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    host: str = Field("localhost", description="Database host name")
    port: int = Field(5432, description="Database port")
    user: str = Field("tracefox", description="Database user")
    password: str = Field("tracefox", description="Database password")
    database: str = Field("tracefox", description="Database name")
    min_pool: int = Field(5, description="Minimum number of connections in pool")
    max_pool: int = Field(100, description="Maximum number of connections in pool")


class RedisSettings(BaseModel):
    host: str = Field("localhost")
    port: int = Field(6379)
    username: Optional[str] = None
    password: Optional[str] = None
    db: int = Field(0)
    max_connections: int = Field(50)
    socket_timeout: float = Field(5.0)


class Neo4jSettings(BaseModel):
    uri: str = Field("neo4j://localhost:7687")
    user: str = Field("neo4j")
    password: str = Field("tracefox")
    max_connection_pool_size: int = Field(100)


class StorageSettings(BaseModel):
    provider: str = Field("s3", description="Storage provider identifier")
    bucket: str = Field("tracefox-artifacts")
    region: Optional[str] = Field(None)


class ObservabilitySettings(BaseModel):
    traces_endpoint: Optional[AnyHttpUrl] = None
    metrics_endpoint: Optional[AnyHttpUrl] = None
    logs_endpoint: Optional[AnyHttpUrl] = None
    sampling_rate: float = Field(0.2, ge=0.0, le=1.0)


class MessagingSettings(BaseModel):
    broker_url: str = Field("amqp://guest:guest@localhost//")
    consumer_groups: List[str] = Field(
        default_factory=lambda: [
            "indexing",
            "review",
            "test-generation",
            "test-execution",
            "rca",
            "learning",
        ]
    )


class AIModelSettings(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    meta_api_key: Optional[str] = None
    krutrim_api_key: Optional[str] = None
    default_temperature: float = Field(0.1, ge=0.0, le=1.0)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRACEFOX_", env_nested_delimiter="__")

    environment: str = Field("local")
    api_gateway_host: str = Field("0.0.0.0")
    api_gateway_port: int = Field(8080)
    postgres: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
    ai_models: AIModelSettings = Field(default_factory=AIModelSettings)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

