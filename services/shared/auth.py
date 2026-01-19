"""Authentication and OAuth helpers used across TraceFox services."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple

import httpx
from pydantic import BaseModel

from services.shared.config import AuthSettings, get_settings


class AuthError(RuntimeError):
    """Raised when authentication or authorization fails."""


class AuthenticatedUser(BaseModel):
    """Represents an authenticated TraceFox user."""

    user_id: str
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    github_access_token: Optional[str] = None


@dataclass
class GitHubIdentity:
    """Subset of GitHub account fields needed by TraceFox."""

    user_id: str
    login: str
    name: Optional[str]
    email: Optional[str]
    avatar_url: Optional[str]


class SessionManager:
    """Issue and validate HMAC-signed bearer tokens."""

    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue(self, user: AuthenticatedUser) -> str:
        payload = {
            "sub": user.user_id,
            "login": user.login,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "gh": user.github_access_token,
            "iat": int(time.time()),
            "exp": int(time.time()) + self._ttl_seconds,
        }
        return self._encode(payload)

    def validate(self, token: str) -> AuthenticatedUser:
        payload = self._decode(token)
        return AuthenticatedUser(
            user_id=payload["sub"],
            login=payload["login"],
            name=payload.get("name"),
            email=payload.get("email"),
            avatar_url=payload.get("avatar_url"),
            github_access_token=payload.get("gh"),
        )

    def _encode(self, payload: Dict[str, object]) -> str:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        encoded_body = base64.urlsafe_b64encode(body).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self._secret, encoded_body.encode("utf-8"), hashlib.sha256
        ).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{encoded_body}.{encoded_signature}"

    def _decode(self, token: str) -> Dict[str, object]:
        parts = token.split(".")
        if len(parts) != 2:
            raise AuthError("Invalid token format")
        body_part, signature_part = parts
        expected_signature = hmac.new(
            self._secret, body_part.encode("utf-8"), hashlib.sha256
        ).digest()
        provided_signature = base64.urlsafe_b64decode(self._pad(signature_part))
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise AuthError("Invalid token signature")
        payload_raw = base64.urlsafe_b64decode(self._pad(body_part))
        payload = json.loads(payload_raw.decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp and exp < int(time.time()):
            raise AuthError("Token expired")
        return payload

    @staticmethod
    def _pad(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return f"{value}{padding}".encode("utf-8")


class OAuthStateStore:
    """State tracker for OAuth flows with TTL enforcement and signature checks."""

    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds
        self._values: Dict[str, float] = {}
        self._lock = Lock()

    def create(self) -> str:
        nonce = secrets.token_urlsafe(32)
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._values[nonce] = expires_at
        payload = {
            "nonce": nonce,
            "exp": int(expires_at),
        }
        return self._encode(payload)

    def consume(self, state: str) -> bool:
        try:
            payload = self._decode(state)
        except AuthError:
            return False
        nonce = payload.get("nonce")
        exp = payload.get("exp")
        if not isinstance(nonce, str) or not isinstance(exp, int):
            return False
        now = time.time()
        if exp < now:
            with self._lock:
                self._values.pop(nonce, None)
            return False
        with self._lock:
            expires_at = self._values.pop(nonce, None)
        if expires_at is None:
            return exp >= now
        return expires_at >= now

    def _encode(self, payload: Dict[str, object]) -> str:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        encoded_body = base64.urlsafe_b64encode(body).decode("utf-8").rstrip("=")
        signature = hmac.new(self._secret, encoded_body.encode("utf-8"), hashlib.sha256).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{encoded_body}.{encoded_signature}"

    def _decode(self, state: str) -> Dict[str, object]:
        parts = state.split(".")
        if len(parts) != 2:
            raise AuthError("Invalid OAuth state format")
        body_part, signature_part = parts
        try:
            expected_signature = hmac.new(
                self._secret, body_part.encode("utf-8"), hashlib.sha256
            ).digest()
            provided_signature = base64.urlsafe_b64decode(self._pad(signature_part))
        except (ValueError, TypeError) as exc:
            raise AuthError("Invalid OAuth state encoding") from exc
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise AuthError("Invalid OAuth state signature")
        try:
            payload_raw = base64.urlsafe_b64decode(self._pad(body_part))
            payload = json.loads(payload_raw.decode("utf-8"))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AuthError("Invalid OAuth state payload") from exc
        return payload

    @staticmethod
    def _pad(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return f"{value}{padding}".encode("utf-8")


@dataclass
class GitHubOAuthResult:
    """Outcome of a GitHub OAuth exchange."""

    identity: GitHubIdentity
    access_token: str


class GitHubOAuthClient:
    """Thin client for exchanging GitHub OAuth codes and retrieving identity."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings
        self._github = settings.github

    def authorization_url(self, state: str) -> str:
        if self._github.dev_mode:
            return f"dev://github-login?state={state}"
        if not self._github.client_id:
            raise AuthError("GitHub OAuth client_id is not configured")
        params = {
            "client_id": self._github.client_id,
            "scope": " ".join(self._github.scope),
            "state": state,
        }
        if self._github.redirect_uri:
            params["redirect_uri"] = self._github.redirect_uri
        query = httpx.QueryParams(params)
        return f"{self._github.login_base}/authorize?{query}"

    async def exchange_code(self, code: str) -> GitHubOAuthResult:
        if self._github.dev_mode:
            login = self._github.dev_login or "tracefox-dev"
            user_id = self._github.dev_user_id or login
            email = self._github.dev_email or f"{login}@example.com"
            return GitHubOAuthResult(
                identity=GitHubIdentity(
                    user_id=user_id,
                    login=login,
                    name=self._github.dev_name or "TraceFox Dev",
                    email=email,
                    avatar_url="https://avatars.githubusercontent.com/u/0?v=4",
                ),
                access_token="dev-token",
            )

        if not self._github.is_configured():
            raise AuthError("GitHub OAuth credentials are missing")

        token = await self._fetch_token(code)
        identity = await self._fetch_identity(token)
        if self._github.allowed_users and identity.login not in self._github.allowed_users:
            raise AuthError("User is not authorised to access TraceFox")
        if self._github.allowed_organizations:
            await self._assert_org_membership(identity.login, token)
        return GitHubOAuthResult(identity=identity, access_token=token)

    async def _fetch_token(self, code: str) -> str:
        token_url = f"{self._github.login_base}/access_token"
        payload = {
            "client_id": self._github.client_id,
            "client_secret": self._github.client_secret,
            "code": code,
            "redirect_uri": self._github.redirect_uri,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    token_url,
                    headers={"Accept": "application/json"},
                    data=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json() if exc.response.headers.get("content-type", "").startswith("application/json") else exc.response.text
            raise AuthError(f"GitHub token exchange failed: {detail}") from exc
        except httpx.RequestError as exc:
            raise AuthError(f"Unable to reach GitHub token endpoint: {exc}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise AuthError(f"GitHub token error: {data.get('error_description') or data['error']}")

        token = data.get("access_token")
        if not token:
            raise AuthError("GitHub did not return an access token")
        return token

    async def _fetch_identity(self, token: str) -> GitHubIdentity:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                user_response = await client.get(f"{self._github.api_base}/user", headers=headers)
                user_response.raise_for_status()
                user_data = user_response.json()
                email = user_data.get("email")
                if not email:
                    emails_response = await client.get(f"{self._github.api_base}/user/emails", headers=headers)
                    emails_response.raise_for_status()
                    for entry in emails_response.json():
                        if entry.get("primary") and entry.get("verified"):
                            email = entry.get("email")
                            break
        except httpx.HTTPStatusError as exc:
            raise AuthError(f"GitHub user lookup failed: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            raise AuthError(f"Unable to reach GitHub API: {exc}") from exc
        # If no email was discoverable from the primary user payload or the
        # /user/emails endpoint, fallback to the GitHub noreply address.
        # This must be executed outside the exception handler so it runs on
        # the successful path when emails are simply absent.
        if not email:
            login = user_data.get("login") or "tracefox"
            email = f"{login}@users.noreply.github.com"
        return GitHubIdentity(
            user_id=str(user_data.get("id")),
            login=user_data.get("login"),
            name=user_data.get("name"),
            email=email,
            avatar_url=user_data.get("avatar_url"),
        )

    async def _assert_org_membership(self, login: str, token: str) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            orgs_response = await client.get(f"{self._github.api_base}/user/orgs", headers=headers)
            orgs_response.raise_for_status()
            orgs = {entry.get("login") for entry in orgs_response.json()}
        allowed = set(self._github.allowed_organizations)
        if not orgs.intersection(allowed):
            raise AuthError("User is not a member of an authorised organisation")

    @property
    def supports_dev_mode(self) -> bool:
        return self._github.dev_mode

    def dev_identity(self, login: str, name: Optional[str], email: Optional[str]) -> GitHubIdentity:
        if not self._github.dev_mode:
            raise AuthError("GitHub dev_mode is disabled")
        fallback_login = self._github.dev_login or login or "tracefox-dev"
        email_value = email or self._github.dev_email or f"{fallback_login}@example.com"
        return GitHubIdentity(
            user_id=self._github.dev_user_id or fallback_login,
            login=login or fallback_login,
            name=name or self._github.dev_name or "TraceFox Developer",
            email=email_value,
            avatar_url="https://avatars.githubusercontent.com/u/0?v=4",
        )


class AuthService:
    """Facade combining OAuth state, session handling, and identity validation."""

    def __init__(self, settings: Optional[AuthSettings] = None) -> None:
        self._settings = settings or get_settings().auth
        self._session_manager = SessionManager(
            self._settings.session_secret, self._settings.session_ttl_seconds
        )
        self._state_store = OAuthStateStore(
            self._settings.session_secret, self._settings.state_ttl_seconds
        )
        self._github_client = GitHubOAuthClient(self._settings)

    def create_login_challenge(self) -> Tuple[str, str]:
        state = self._state_store.create()
        url = self._github_client.authorization_url(state)
        return url, state

    async def complete_login(self, code: str, state: str) -> Tuple[str, AuthenticatedUser]:
        if not self._state_store.consume(state):
            raise AuthError("Invalid or expired OAuth state")
        result = await self._github_client.exchange_code(code)
        identity = result.identity
        user = AuthenticatedUser(
            user_id=identity.user_id,
            login=identity.login,
            name=identity.name,
            email=identity.email,
            avatar_url=identity.avatar_url,
            github_access_token=result.access_token,
        )
        token = self._session_manager.issue(user)
        return token, user

    def validate_token(self, token: str) -> AuthenticatedUser:
        return self._session_manager.validate(token)

    def dev_login(self, login: str, name: Optional[str], email: Optional[str]) -> Tuple[str, AuthenticatedUser]:
        identity = self._github_client.dev_identity(login, name, email)
        user = AuthenticatedUser(
            user_id=identity.user_id,
            login=identity.login,
            name=identity.name,
            email=identity.email,
            avatar_url=identity.avatar_url,
            github_access_token=None,
        )
        token = self._session_manager.issue(user)
        return token, user

    @property
    def dev_mode_enabled(self) -> bool:
        return self._github_client.supports_dev_mode


_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    """Reset global auth service (useful for tests)."""

    global _auth_service
    _auth_service = None


__all__ = [
    "AuthError",
    "AuthService",
    "AuthenticatedUser",
    "GitHubIdentity",
    "SessionManager",
    "OAuthStateStore",
    "get_auth_service",
    "reset_auth_service",
]
