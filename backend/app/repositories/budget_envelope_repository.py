from __future__ import annotations

from typing import Protocol

from app.domain.budget_envelope import BudgetEnvelope
from app.domain.transaction import TransactionKind


class BudgetEnvelopeRepository(Protocol):
    def list(self, *, profile_id: str | None = None) -> list[BudgetEnvelope]: ...
    def upsert(self, envelope: BudgetEnvelope, *, profile_id: str | None = None) -> BudgetEnvelope: ...
    def delete(self, envelope_id: str, *, profile_id: str | None = None) -> bool: ...
    def delete_by_category(
        self,
        category: str,
        subcategory: str | None = None,
        kind: TransactionKind | None = None,
        *,
        profile_id: str | None = None,
    ) -> int: ...
