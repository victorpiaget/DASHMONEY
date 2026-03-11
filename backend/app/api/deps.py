from __future__ import annotations

from functools import lru_cache

from app.repositories.sql_account_repository import SqlAccountRepository
from app.repositories.sql_transaction_repository import SqlTransactionRepository
from app.repositories.sql_instrument_repository import SqlInstrumentRepository
from app.repositories.sql_trade_repository import SqlTradeRepository
from app.repositories.sql_portfolio_repository import SqlPortfolioRepository
from app.repositories.sql_portfolio_snapshot_repository import SqlPortfolioSnapshotRepository
from app.repositories.sql_price_repository import SqlPriceRepository
from app.repositories.sql_identity_repository import SqlProfileRepository, SqlWorkspaceRepository


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