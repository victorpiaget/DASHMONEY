from __future__ import annotations

from typing import Protocol, Iterable, Optional
import datetime as dt
from uuid import UUID

from app.domain.transaction import Transaction, TransactionKind
from app.domain.signed_money import SignedMoney




class TransactionRepository(Protocol):
    def add(self, tx: Transaction) -> None:
        ...

    def list(self, account_id: Optional[str] = None) -> list[Transaction]:
        ...

    def get(self, tx_id: UUID) -> Transaction | None:
        ...

    def next_sequence(self, account_id: str, date: dt.date) -> int:
        ...
    def delete(self, *, account_id: str, tx_id: UUID) -> bool:
        """Return True if deleted, False if not found."""
        ...

    def update(
        self,
        *,
        account_id: str,
        tx_id: UUID,
        category: str | None = None,
        subcategory: str | None = None,
        label: str | None = None,
        date: dt.date | None = None,
        amount: SignedMoney | None = None,
        kind: TransactionKind | None = None,
    ) -> Transaction:
        ...