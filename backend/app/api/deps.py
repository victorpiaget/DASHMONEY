from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.settings import get_settings
from app.repositories.json_account_repository import JsonAccountRepository
from app.repositories.jsonl_transaction_repository import JsonlTransactionRepository


@lru_cache
def get_account_repo() -> JsonAccountRepository:
    settings = get_settings()
    return JsonAccountRepository(accounts_path=settings.data_dir / "accounts.json")


@lru_cache
def get_tx_repo() -> JsonlTransactionRepository:
    settings = get_settings()
    account_repo = get_account_repo()
    return JsonlTransactionRepository(tx_path=settings.data_dir / "transactions.jsonl", account_repo=account_repo)
