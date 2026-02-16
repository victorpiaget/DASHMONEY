from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.settings import get_settings
from app.repositories.json_account_repository import JsonAccountRepository
from app.repositories.jsonl_transaction_repository import JsonlTransactionRepository

from app.repositories.json_portfolio_repository import JsonPortfolioRepository
from app.repositories.jsonl_portfolio_snapshot_repository import JsonlPortfolioSnapshotRepository

from app.repositories.json_instrument_repository import JsonInstrumentRepository
from app.repositories.jsonl_trade_repository import JsonlTradeRepository


@lru_cache
def get_account_repo() -> JsonAccountRepository:
    settings = get_settings()
    return JsonAccountRepository(accounts_path=settings.data_dir / "accounts.json")


@lru_cache
def get_tx_repo() -> JsonlTransactionRepository:
    settings = get_settings()
    account_repo = get_account_repo()
    return JsonlTransactionRepository(tx_path=settings.data_dir / "transactions.jsonl", account_repo=account_repo)


@lru_cache
def get_portfolio_repo() -> JsonPortfolioRepository:
    settings = get_settings()
    return JsonPortfolioRepository(portfolios_path=settings.data_dir / "portfolios.json")

@lru_cache
def get_portfolio_snapshot_repo() -> JsonlPortfolioSnapshotRepository:
    settings = get_settings()
    return JsonlPortfolioSnapshotRepository(snapshots_path=settings.data_dir / "portfolio_snapshots.jsonl")

@lru_cache
def get_instrument_repo() -> JsonInstrumentRepository:
    settings = get_settings()
    return JsonInstrumentRepository(instruments_path=settings.data_dir / "instruments.json")

@lru_cache
def get_trade_repo() -> JsonlTradeRepository:
    settings = get_settings()
    return JsonlTradeRepository(trades_path=settings.data_dir / "trades.jsonl")