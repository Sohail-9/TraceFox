"""Authentication routes for TraceFox API Gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from services.shared.auth import (
    AuthError,
    AuthService,
    AuthenticatedUser,
    get_auth_service,
)

router = APIRouter(prefix="/auth/github", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class LoginResponse(BaseModel):
    authorization_url: str
    state: str


class CallbackRequest(BaseModel):
    code: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
    github_token: str | None = None


class DevLoginRequest(BaseModel):
    login: str
    name: str | None = None
    email: str | None = None


@router.get("/login", response_model=LoginResponse)
async def github_login(service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    try:
        url, state = service.create_login_challenge()
    except AuthError as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return LoginResponse(authorization_url=url, state=state)


@router.post("/callback", response_model=TokenResponse)
async def github_callback(
    payload: CallbackRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    try:
        token, user = await service.complete_login(payload.code, payload.state)
    except AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return TokenResponse(access_token=token, user=user, github_token=user.github_access_token)


@router.post("/dev-login", response_model=TokenResponse)
async def github_dev_login(
    payload: DevLoginRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    if not service.dev_mode_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "GitHub dev_mode is disabled; configure auth.github.dev_mode=true for local testing.",
        )
    token, user = service.dev_login(payload.login, payload.name, payload.email)
    return TokenResponse(access_token=token, user=user, github_token=user.github_access_token)


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        return service.validate_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc


__all__ = ["router", "require_user"]
