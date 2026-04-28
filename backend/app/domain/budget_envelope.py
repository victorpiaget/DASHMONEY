from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from app.domain.money import Currency, Money
from app.domain.transaction import TransactionKind


@dataclass(frozen=True)
class BudgetEnvelope:
    id: UUID
    category: str
    subcategory: Optional[str]
    kind: TransactionKind
    amount: Money

    @staticmethod
    def create(
        *,
        category: str,
        kind: TransactionKind,
        amount: Money,
        subcategory: Optional[str] = None,
        id: Optional[UUID] = None,
    ) -> "BudgetEnvelope":
        if not isinstance(category, str) or category.strip() == "":
            raise ValueError("category cannot be empty")

        if kind not in (TransactionKind.INCOME, TransactionKind.EXPENSE):
            raise ValueError("kind must be INCOME or EXPENSE")

        if not isinstance(amount, Money):
            raise ValueError("amount must be a Money instance")

        if amount.amount <= Decimal("0"):
            raise ValueError("amount must be strictly positive")

        norm_category = category.strip()

        if subcategory is None:
            norm_subcategory = None
        else:
            if not isinstance(subcategory, str) or subcategory.strip() == "":
                raise ValueError("subcategory cannot be empty if provided")
            norm_subcategory = subcategory.strip()

        return BudgetEnvelope(
            id=id or uuid4(),
            category=norm_category,
            subcategory=norm_subcategory,
            kind=kind,
            amount=amount,
        )
