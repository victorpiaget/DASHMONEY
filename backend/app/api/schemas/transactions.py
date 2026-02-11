from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, Field

from app.domain.money import Currency
from app.domain.transaction import TransactionKind


class TransactionCreateRequest(BaseModel):
    account_id: str = Field(..., min_length=1)
    date: date
    amount: str = Field(..., min_length=1, pattern=r"^-?\d+(\.\d{1,2})?$", examples=["-12.34", "1000.00"],description="Signed amount as string, e.g. '-12.34' or '1000'")
    currency: Currency
    kind: TransactionKind
    category: str = Field(..., min_length=1)
    subcategory: str | None = None
    label: str | None = None


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    date: date
    sequence: int
    amount: str
    currency: Currency
    kind: TransactionKind
    category: str
    subcategory: str | None
    label: str | None
    created_at: datetime
