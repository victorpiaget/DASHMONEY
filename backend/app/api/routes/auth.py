from __future__ import annotations

import datetime as dt
import os
from typing import Optional

from fastapi import APIRouter, Body, Cookie, HTTPException, Response

from app.api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.identity.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expires_at,
    verify_password,
)
from app.repositories.sql_identity_repository import SqlProfileRepository, SqlWorkspaceRepository
from app.repositories.sql_refresh_token_repository import SqlRefreshTokenRepository
from app.repositories.sql_user_repository import SqlUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/auth/refresh"
_REFRESH_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 jours en secondes
_COOKIE_SECURE = os.getenv("DASHMONEY_COOKIE_SECURE", "false").lower() == "true"


def _user_repo() -> SqlUserRepository:
    return SqlUserRepository()


def _rt_repo() -> SqlRefreshTokenRepository:
    return SqlRefreshTokenRepository()


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="strict",
        path=_REFRESH_COOKIE_PATH,
        max_age=_REFRESH_COOKIE_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
    )


def _issue_token_pair(user_id: str, email: str) -> TokenResponse:
    """Create + persist a new access/refresh token pair."""
    access = create_access_token(user_id=user_id, email=email)
    raw_refresh = create_refresh_token()
    _rt_repo().create(
        user_id=user_id,
        token_hash=hash_token(raw_refresh),
        expires_at=refresh_token_expires_at(),
    )
    return TokenResponse(access_token=access, refresh_token=raw_refresh)


@router.post("/register", status_code=201, response_model=UserResponse)
def register(payload: RegisterRequest) -> UserResponse:
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    try:
        user = _user_repo().create(
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Auto-créer workspace + profil par défaut pour le nouvel utilisateur
    workspace = SqlWorkspaceRepository().create_workspace(name="Mon espace")
    profile_repo = SqlProfileRepository()
    profile = profile_repo.create_profile(
        workspace_id=workspace.id,
        display_name="Principal",
    )
    profile_repo.grant_profile_access(
        user_id=user.id,
        profile_id=profile.id,
        permission="OWNER",
    )

    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response) -> TokenResponse:
    repo = _user_repo()
    user = repo.get_by_email(payload.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    if not verify_password(payload.password, repo.get_password_hash(user.id)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_resp = _issue_token_pair(user_id=user.id, email=user.email)
    _set_refresh_cookie(response, token_resp.refresh_token)
    return token_resp


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    payload: Optional[RefreshRequest] = Body(default=None),
    refresh_token: Optional[str] = Cookie(default=None),
) -> TokenResponse:
    # Cookie prioritaire (browser), fallback sur body (tests / API clients)
    raw_token = refresh_token or (payload.refresh_token if payload else None)
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    rt_repo = _rt_repo()
    token_hash = hash_token(raw_token)
    rt = rt_repo.get_by_hash(token_hash)

    if rt is None or rt.revoked:
        # Token inconnu ou déjà révoqué → possible vol, on révoque tout
        if rt is not None:
            rt_repo.revoke_all_for_user(rt.user_id)
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    now = dt.datetime.now(dt.timezone.utc)
    if rt.expires_at.replace(tzinfo=dt.timezone.utc) < now:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Rotation : révoquer l'ancien avant d'en émettre un nouveau
    rt_repo.revoke(rt.id)

    user = _user_repo().get(rt.user_id)
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")

    token_resp = _issue_token_pair(user_id=user.id, email=user.email)
    _set_refresh_cookie(response, token_resp.refresh_token)
    return token_resp


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, response: Response) -> None:
    token_hash = hash_token(payload.refresh_token)
    rt = _rt_repo().get_by_hash(token_hash)
    if rt is not None and not rt.revoked:
        _rt_repo().revoke(rt.id)
    _clear_refresh_cookie(response)
