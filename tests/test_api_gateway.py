from __future__ import annotations

import json
import os
import random
from typing import Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_config() -> Dict[str, object]:
    return {
        "environment": "test",
        "api_gateway": {
            "host": "0.0.0.0",
            "port": 8080,
            "allowed_origins": [
                "http://localhost",
                "http://localhost:3000",
                "http://127.0.0.1",
            ],
        },
        "postgres": {
            "host": "127.0.0.1",
            "port": 5432,
            "user": "tracefox",
            "password": "tracefox",
            "database": "tracefox",
            "min_pool": 1,
            "max_pool": 5,
            "connection_timeout_seconds": 5,
            "statement_timeout_seconds": 5,
            "max_idle_seconds": 60,
        },
        "redis": {
            "host": "127.0.0.1",
            "port": 6379,
            "username": None,
            "password": "local-pass",
            "db": 0,
            "max_connections": 10,
            "socket_timeout_seconds": 5,
            "key_version": "vtest",
            "default_ttl_seconds": 300,
        },
        "neo4j": {
            "uri": "neo4j://127.0.0.1:7687",
            "user": "neo4j",
            "password": "tracefox",
            "max_connection_pool_size": 10,
            "connection_acquisition_timeout_seconds": 5,
            "encrypted": False,
        },
        "storage": {
            "provider": "s3",
            "bucket": "tracefox-test",
            "region": "us-east-1",
            "kms_key_id": None,
        },
        "observability": {
            "traces_endpoint": None,
            "metrics_endpoint": None,
            "logs_endpoint": None,
            "sampling_ratio": 0.1,
            "exporter_protocol": None,
        },
        "messaging": {
            "broker_url": "memory://",
            "consumer_groups": [
                "indexing",
                "ai-review",
                "test-generation",
                "test-execution",
                "rca",
                "learning",
            ],
            "queue_max_size": 512,
            "delivery_timeout_seconds": 5,
        },
        "retry": {
            "enabled": True,
            "initial_interval_seconds": 0.1,
            "multiplier": 2.0,
            "max_interval_seconds": 1.0,
            "max_elapsed_time_seconds": 5.0,
            "randomization_factor": 0.1,
            "max_retries": 3,
        },
        "circuit_breaker": {
            "failure_rate_threshold": 0.5,
            "slow_call_rate_threshold": 0.5,
            "slow_call_duration_threshold_seconds": 1.0,
            "sliding_window_size": 10,
            "minimum_number_of_calls": 5,
            "wait_duration_in_open_state_seconds": 2.0,
            "permitted_calls_in_half_open_state": 2,
        },
        "cache": {
            "namespace": "tracefox",
            "version": "vtest",
            "default_ttl_seconds": 300,
        },
        "security": {
            "jwt_issuer": None,
            "jwks_url": None,
            "allowed_audiences": [],
            "enforce_mtls": False,
            "audit_topic": None,
        },
        "rate_limit": {
            "global_rps": 200,
            "burst": 400,
            "per_tenant_rps": 60,
        },
        "ai_models": {
            "default_temperature": 0.2,
            "providers": {
                "stub": {"api_key": "test", "model": "stub-model", "endpoint": "http://stub"}
            },
        },
        "qdrant": {
            "host": "127.0.0.1",
            "port": 6333,
            "grpc_port": 6334,
            "api_key": None,
            "prefer_grpc": False,
            "tls_enabled": False,
            "replication_factor": 1,
            "write_consistency_factor": 1,
            "snapshot_schedule_cron": None,
            "backup_storage_uri": None,
            "backup_schedule_cron": None,
            "collections": [
                {
                    "name": "codebase-index",
                    "vector_size": 128,
                    "distance": "Cosine",
                    "shard_number": 1,
                    "on_disk_payload": True,
                }
            ],
        },
        "quality": {"flaky_threshold": 0.3},
        "auth": {
            "session_secret": "unit-test-secret",
            "session_ttl_seconds": 3600,
            "state_ttl_seconds": 300,
            "github": {
                "dev_mode": True,
                "dev_email": "dev@tracefox.test",
                "scope": ["read:user", "user:email"],
            },
        },
    }


@pytest.fixture(scope="session")
def api_app(tmp_path_factory) -> FastAPI:
    config_path = tmp_path_factory.mktemp("cfg") / "tracefox-test.json"
    config_path.write_text(json.dumps(_build_config()))
    os.environ["TRACEFOX_CONFIG_FILE"] = str(config_path)
    data_path = tmp_path_factory.mktemp("data") / "tracefox.db"
    os.environ["TRACEFOX_DATA_PATH"] = str(data_path)

    from services.shared.config import reload_settings

    reload_settings()
    from services.shared.auth import reset_auth_service
import services.api_gateway.routes.github as github_routes
import services.api_gateway.service_registry as registry_module

    reset_auth_service()

    from services.api_gateway.main import app

    return app


@pytest.fixture()
def client(api_app) -> TestClient:
    return TestClient(api_app)


@pytest.fixture(autouse=True)
def _seed_random() -> None:
    random.seed(0)


def _auth_headers(client: TestClient) -> Dict[str, str]:
    response = client.post(
        "/auth/github/dev-login",
        json={
            "login": "tester",
            "name": "TraceFox Tester",
            "email": "tester@example.com",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    token = payload["access_token"]
    assert payload["github_token"] is None
    return {"Authorization": f"Bearer {token}"}


def test_auth_dev_login_flow(client: TestClient) -> None:
    login_response = client.get("/auth/github/login")
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["authorization_url"].startswith("dev://")
    assert payload["state"]

    callback_response = client.post(
        "/auth/github/callback",
        json={"code": "dummy", "state": payload["state"]},
    )
    assert callback_response.status_code == 200
    data = callback_response.json()
    assert data["access_token"]
    assert data["github_token"] == "dev-token"


def _login_and_get_token(client: TestClient) -> Dict[str, str]:
    login_response = client.get("/auth/github/login")
    assert login_response.status_code == 200
    state = login_response.json()["state"]
    callback_response = client.post(
        "/auth/github/callback",
        json={"code": "dummy", "state": state},
    )
    assert callback_response.status_code == 200
    data = callback_response.json()
    assert data["github_token"] == "dev-token"
    return {
        "Authorization": f"Bearer {data['access_token']}",
    }


def test_github_list_repositories_endpoint(client: TestClient, monkeypatch) -> None:
    headers = _login_and_get_token(client)

    async def fake_list_repositories(token: str, *, api_base: str, per_page: int = 50, max_pages: int = 5):  # type: ignore[override]
        return [
            {
                "id": 101,
                "full_name": "tracefox/alpha",
                "description": "Alpha repo",
                "clone_url": "https://github.com/tracefox/alpha.git",
                "default_branch": "main",
                "html_url": "https://github.com/tracefox/alpha",
                "private": False,
                "owner": {"login": "tracefox"},
            }
        ]

    monkeypatch.setattr(github_routes.github_client, "list_repositories", fake_list_repositories)

    response = client.get("/integrations/github/repos", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["repositories"][0]["full_name"] == "tracefox/alpha"


def test_github_track_repository_endpoint(client: TestClient, monkeypatch) -> None:
    headers = _login_and_get_token(client)

    async def fake_get_repository(token: str, *, api_base: str, full_name: str):  # type: ignore[override]
        return {
            "id": 202,
            "full_name": full_name,
            "description": "Tracked repo",
            "clone_url": "https://github.com/tracefox/beta.git",
            "default_branch": "main",
            "html_url": "https://github.com/tracefox/beta",
            "private": False,
            "owner": {"login": full_name.split("/")[0]},
        }

    async def fake_schedule_clone(self, *, user_id: str, repo_data: Dict[str, object], github_token: str):  # type: ignore[override]
        return {"job_id": "job-123", "status": "queued"}

    monkeypatch.setattr(github_routes.github_client, "get_repository", fake_get_repository)
    monkeypatch.setattr(
        registry_module.registry.repositories,
        "schedule_clone",
        fake_schedule_clone.__get__(registry_module.registry.repositories, type(registry_module.registry.repositories)),
    )

    response = client.post(
        "/integrations/github/repos",
        json={"full_name": "tracefox/beta"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["repository"]["full_name"] == "tracefox/beta"
    assert payload["clone_job"]["status"] == "queued"


def _webhook_payload() -> Dict[str, object]:
    return {
        "event_type": "pull_request",
        "action": "opened",
        "repository": {
            "id": "repo-123",
            "name": "tracefox/backend",
            "url": "https://github.com/tracefox/backend",
            "default_branch": "main",
        },
        "pull_request": {
            "number": 42,
            "title": "Add compliance checks",
            "author": "sohail",
            "source_branch": "feature/compliance",
            "target_branch": "main",
            "diff_url": "https://github.com/tracefox/backend/pull/42.diff",
        },
        "files": [],
    }


def _extract_pr_id(payload: Dict[str, object]) -> str:
    repository = payload["repository"]  # type: ignore[index]
    pull_request = payload["pull_request"]  # type: ignore[index]
    return f"{repository['id']}:{pull_request['number']}"


def test_webhook_review_and_execution_flow(client: TestClient) -> None:
    payload = _webhook_payload()
    pr_id = _extract_pr_id(payload)
    headers = _auth_headers(client)

    webhook_response = client.post("/webhooks/github", json=payload, headers=headers)
    assert webhook_response.status_code == 202
    webhook_data = webhook_response.json()
    assert webhook_data["status"] == "accepted"
    assert webhook_data["review_id"]

    review_response = client.get(
        f"/reviews/pr/{pr_id}",
        params={"include_tests": "true", "include_rca": "true"},
        headers=headers,
    )
    assert review_response.status_code == 200
    review_data = review_response.json()
    assert review_data["pr_id"] == pr_id
    assert review_data["findings"]

    generation_response = client.post(
        "/tests/generate",
        json={
            "pr_id": pr_id,
            "finding_ids": [],
            "test_types": ["unit", "integration"],
            "prioritize": True,
        },
        headers=headers,
    )
    assert generation_response.status_code == 202
    generation_data = generation_response.json()
    test_ids: List[str] = [item["id"] for item in generation_data["test_cases"]]
    assert test_ids

    execution_response = client.post(
        "/tests/execute",
        json={
            "pr_id": pr_id,
            "test_case_ids": test_ids,
            "parallel": True,
            "timeout_seconds": 300,
        },
        headers=headers,
    )
    assert execution_response.status_code == 202
    execution_data = execution_response.json()
    execution_id = execution_data["execution_id"]
    assert execution_data["status"] == "completed"

    results_response = client.get(f"/tests/results/{execution_id}", headers=headers)
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["execution_id"] == execution_id
    assert len(results_data["results"]) == len(test_ids)

    flaky_response = client.get(
        "/tests/flaky",
        params={"repository_id": payload["repository"]["id"], "threshold": 0.2},
        headers=headers,
    )
    assert flaky_response.status_code == 200

    operations_response = client.get("/operations/console", headers=headers)
    assert operations_response.status_code == 200
    operations_data = operations_response.json()
    assert operations_data["total_prs"] >= 1
    assert operations_data["checklist"]["execution"] is True
    summary_per_pr = operations_data["summary"]["per_pr"]
    assert pr_id in summary_per_pr
    assert summary_per_pr[pr_id]["total_findings"] == review_data["total_findings"]
    tests_per_pr = operations_data["tests"]["per_pr"]
    assert tests_per_pr.get(pr_id) == len(test_ids)
    executions_per_pr = operations_data["executions"]["per_pr_counts"]
    assert executions_per_pr.get(pr_id, 0) >= 1
    payload_snapshot = operations_data.get("latest_payload") or {}
    assert payload_snapshot.get("pull_request", {}).get("number") == payload["pull_request"]["number"]

    rca_response = client.get(f"/rca/{execution_id}", headers=headers)
    assert rca_response.status_code in {200, 404}


def test_health_and_feedback_endpoints(client: TestClient) -> None:
    health_response = client.get("/healthz")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    headers = _auth_headers(client)
    feedback_response = client.post(
        "/feedback",
        json={
            "user_id": "tester",
            "target_type": "review",
            "target_id": "review-123",
            "reaction": "upvote",
            "comment": "Helpful findings",
        },
        headers=headers,
    )
    assert feedback_response.status_code == 201
    payload = feedback_response.json()
    assert payload["feedback_id"].startswith("feedback-")


def test_webhook_options_preflight(client: TestClient) -> None:
    response = client.options(
        "/webhooks/github",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code in (200, 204)
    headers = {k.lower(): v for k, v in response.headers.items()}
    assert "access-control-allow-methods" in headers
