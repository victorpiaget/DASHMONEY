from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi import Query

from app.domain.user import User
from app.identity.auth import decode_access_token

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
from app.repositories.sql_budget_envelope_repository import SqlBudgetEnvelopeRepository
from app.repositories.sql_category_repository import SqlCategoryRepository
from app.repositories.sql_exchange_rate_repository import SqlExchangeRateRepository

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


@lru_cache
def get_category_repo():
    return SqlCategoryRepository()


@lru_cache
def get_exchange_rate_repo():
    return SqlExchangeRateRepository()


@lru_cache
def get_budget_envelope_repo():
    return SqlBudgetEnvelopeRepository()


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
    profile_repo = get_profile_repo()

    if profile_id is None or not profile_id.strip():
        pid = profile_repo.get_default_profile_id_for_user(user.id)
        if pid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No profile found for this user",
            )
    else:
        pid = profile_id.strip()
        if not profile_repo.has_profile_access(user_id=user.id, profile_id=pid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to profile '{pid}'",
            )

    permission = profile_repo.get_profile_permission(user_id=user.id, profile_id=pid) or "READ"
    return RequestContext(user_id=user.id, profile_id=pid, permission=permission)


async def get_write_context(
    ctx: RequestContext = Depends(get_request_context),
) -> RequestContext:
    if ctx.permission == "READ":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only access to this profile",
        )
    return ctx