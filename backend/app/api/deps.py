from __future__ import annotations

from functools import lru_cache

from app.repositories.sql_account_repository import SqlAccountRepository
from app.repositories.sql_transaction_repository import SqlTransactionRepository
from app.repositories.sql_instrument_repository import SqlInstrumentRepository
from app.repositories.sql_trade_repository import SqlTradeRepository
from app.repositories.sql_portfolio_repository import SqlPortfolioRepository
from app.repositories.sql_portfolio_snapshot_repository import SqlPortfolioSnapshotRepository
from app.repositories.sql_price_repository import SqlPriceRepository


@lru_cache
def get_account_repo():
    return SqlAccountRepository()


@lru_cache
def get_tx_repo():
    account_repo = get_account_repo()
    return SqlTransactionRepository(tx_account_repo=account_repo)
   
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