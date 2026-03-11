from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi import Query

from app.domain.user import User
from app.identity.auth import decode_access_token
from app.identity.profile_scope import resolve_profile_id
from app.identity.request_context import RequestContext
from app.repositories.sql_account_repository import SqlAccountRepository
from app.repositories.sql_transaction_repository import SqlTransactionRepository
from app.repositories.sql_instrument_repository import SqlInstrumentRepository
from app.repositories.sql_trade_repository import SqlTradeRepository
from app.repositories.sql_portfolio_repository import SqlPortfolioRepository
from app.repositories.sql_portfolio_snapshot_repository import SqlPortfolioSnapshotRepository
from app.repositories.sql_price_repository import SqlPriceRepository
from app.repositories.sql_identity_repository import SqlProfileRepository, SqlWorkspaceRepository
from app.repositories.sql_refresh_token_repository import SqlRefreshTokenRepository
from app.repositories.sql_user_repository import SqlUserRepository

_bearer = HTTPBearer(auto_error=True)


@lru_cache
def get_account_repo():
    return SqlAccountRepository()


@lru_cache
def get_tx_repo():
    return SqlTransactionRepository()
   
@lru_cache
def get_portfolio_repo():
    return SqlPortfolioRepository()

@lru_cache
def get_portfolio_snapshot_repo():
    return SqlPortfolioSnapshotRepository()

@lru_cache
def get_instrument_repo():
    return SqlInstrumentRepository()

@lru_cache
def get_trade_repo():
    return SqlTradeRepository()

@lru_cache
def get_price_repo():
    return SqlPriceRepository()

@lru_cache
def get_workspace_repo():
    return SqlWorkspaceRepository()


@lru_cache
def get_profile_repo():
    return SqlProfileRepository()


@lru_cache
def get_user_repo():
    return SqlUserRepository()


@lru_cache
def get_refresh_token_repo():
    return SqlRefreshTokenRepository()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id: str = payload.get("sub", "")
    try:
        user = get_user_repo().get(user_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.is_disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return user


async def get_request_context(
    user: User = Depends(get_current_user),
    profile_id: str | None = Query(default=None),
) -> RequestContext:
    pid = resolve_profile_id(profile_id)
    if not get_profile_repo().has_profile_access(user_id=user.id, profile_id=pid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to profile '{pid}'",
        )
    return RequestContext(user_id=user.id, profile_id=pid)