from __future__ import annotations

from typing import Protocol, Iterable, Optional
import datetime as dt
from uuid import UUID

from app.domain.transaction import Transaction, TransactionKind
from app.domain.signed_money import SignedMoney




class TransactionRepository(Protocol):
    def add(self, tx: Transaction, *, profile_id: str | None = None) -> None:
        ...

    def list(self, account_id: Optional[str] = None, *, profile_id: str | None = None) -> list[Transaction]:
        ...

    def get(self, tx_id: UUID, *, profile_id: str | None = None) -> Transaction | None:
        ...

    def next_sequence(self, account_id: str, date: dt.date, *, profile_id: str | None = None) -> int:
        ...
    def delete(self, *, account_id: str, tx_id: UUID, profile_id: str | None = None) -> bool:
        """Return True if deleted, False if not found."""
        ...

    def update(
        self,
        *,
        account_id: str,
        tx_id: UUID,
        profile_id: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        label: str | None = None,
        date: dt.date | None = None,
        amount: SignedMoney | None = None,
        kind: TransactionKind | None = None,
    ) -> Transaction:
        ...

    # Transfers (2 legs)
    def update_transfer(
        self,
        *,
        transfer_id: UUID,
        new_date: dt.date | None = None,
        new_amount_pos: SignedMoney | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        label: str | None = None,
        profile_id: str | None = None,
    ) -> tuple[Transaction, Transaction]:
        ...

    def delete_transfer(self, *, transfer_id: UUID, profile_id: str | None = None) -> tuple[UUID, UUID]:
        ...

    def link_as_transfer(
        self, *, tx_from_id: UUID, tx_to_id: UUID, profile_id: str | None = None
    ) -> tuple[Transaction, Transaction]:
        ...