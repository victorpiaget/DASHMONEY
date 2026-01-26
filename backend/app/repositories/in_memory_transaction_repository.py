from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt
from uuid import UUID

from app.domain.transaction import Transaction


@dataclass
class InMemoryTransactionRepository:
    """
    Repo V0 en mémoire.
    - Déterministe
    - Facile à tester
    - Suffisant pour brancher API + engine
    """
    _items: list[Transaction] = field(default_factory=list)

    def add(self, tx: Transaction) -> None:
        if self.get(tx.id) is not None:
            raise ValueError(f"Transaction with id {tx.id} already exists")
        self._items.append(tx)

    def list(self, account_id: str | None = None) -> list[Transaction]:
        items = self._items
        if account_id is not None:
            items = [t for t in items if t.account_id == account_id]

        # Tri déterministe : date, sequence, created_at, id
        return sorted(
            items,
            key=lambda t: (t.date, t.sequence, t.created_at, str(t.id)),
        )

    def get(self, tx_id: UUID) -> Transaction | None:
        for t in self._items:
            if t.id == tx_id:
                return t
        return None

    def next_sequence(self, account_id: str, date: dt.date) -> int:
        """
        Sequence auto = 1 + max(sequence) sur (account_id, date).
        Si aucune transaction ce jour-là -> 1
        """
        max_seq = 0
        for t in self._items:
            if t.account_id == account_id and t.date == date:
                if t.sequence > max_seq:
                    max_seq = t.sequence
        return max_seq + 1
