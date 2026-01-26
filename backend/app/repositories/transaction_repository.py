from __future__ import annotations

from typing import Protocol, Iterable, Optional
import datetime as dt
from uuid import UUID

from app.domain.transaction import Transaction


class TransactionRepository(Protocol):
    def add(self, tx: Transaction) -> None:
        ...

    def list(self, account_id: Optional[str] = None) -> list[Transaction]:
        ...

    def get(self, tx_id: UUID) -> Transaction | None:
        ...

    def next_sequence(self, account_id: str, date: dt.date) -> int:
        ...
