from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.domain.signed_money import SignedMoney


class TransactionKind(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    INVESTMENT = "INVESTMENT"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass(frozen=True)
class Transaction:
    id: UUID
    account_id: str
    date: dt.date
    sequence: int
    amount: SignedMoney
    kind: TransactionKind
    category: str
    subcategory: Optional[str]
    label: Optional[str]
    created_at: dt.datetime

    @staticmethod
    def create(
        *,
        account_id: str,
        date: dt.date,
        sequence: int,
        amount: SignedMoney,
        kind: TransactionKind,
        category: str,
        subcategory: Optional[str] = None,
        label: Optional[str] = None,
        id: Optional[UUID] = None,
        created_at: Optional[dt.datetime] = None,
    ) -> "Transaction":
        if not isinstance(account_id, str) or account_id.strip() == "":
            raise ValueError("account_id cannot be empty")

        # ✅ maintenant dt.date est accessible sans collision
        if not isinstance(date, dt.date):
            raise ValueError("date must be a date")

        if not isinstance(sequence, int) or sequence < 1:
            raise ValueError("sequence must be an integer >= 1")

        if not isinstance(amount, SignedMoney):
            raise ValueError("amount must be a SignedMoney")

        if not isinstance(kind, TransactionKind):
            raise ValueError("kind must be a TransactionKind")

        if not isinstance(category, str) or category.strip() == "":
            raise ValueError("category cannot be empty")

        norm_account_id = account_id.strip()
        norm_category = category.strip()

        if subcategory is None:
            norm_subcategory = None
        else:
            if not isinstance(subcategory, str) or subcategory.strip() == "":
                raise ValueError("subcategory cannot be empty if provided")
            norm_subcategory = subcategory.strip()

        if label is None:
            norm_label = None
        else:
            if not isinstance(label, str) or label.strip() == "":
                raise ValueError("label cannot be empty if provided")
            norm_label = label.strip()

        # Cohérence signe ↔ kind
        amt = amount.amount

        if amt == 0:
            raise ValueError("Transaction amount cannot be zero")

        if kind == TransactionKind.INCOME and not (amt > 0):
            raise ValueError("INCOME transactions must have a positive amount")
        if kind == TransactionKind.EXPENSE and not (amt < 0):
            raise ValueError("EXPENSE transactions must have a negative amount")

        final_id = id or uuid4()

        if created_at is None:
            final_created_at = dt.datetime.now(dt.timezone.utc)
        else:
            if not isinstance(created_at, dt.datetime):
                raise ValueError("created_at must be a datetime")
            if created_at.tzinfo is None:
                raise ValueError("created_at must be timezone-aware (UTC recommended)")
            final_created_at = created_at.astimezone(dt.timezone.utc)

        return Transaction(
            id=final_id,
            account_id=norm_account_id,
            date=date,
            sequence=sequence,
            amount=amount,
            kind=kind,
            category=norm_category,
            subcategory=norm_subcategory,
            label=norm_label,
            created_at=final_created_at,
        )
