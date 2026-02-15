from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field

from app.domain.money import Currency
from app.domain.transaction import TransactionKind


class AccountTransactionCreateRequest(BaseModel):
    date: dt.date
    amount: str = Field(
        ...,
        min_length=1,
        pattern=r"^-?\d+(\.\d{1,2})?$",
        examples=["-12.34", "1000.00"],
        description="Signed amount as string, e.g. '-12.34' or '1000'",
    )
    kind: TransactionKind
    category: str = Field(..., min_length=1)
    subcategory: str | None = None
    label: str | None = None


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    date: dt.date
    sequence: int
    amount: str
    currency: Currency
    kind: TransactionKind
    category: str
    subcategory: str | None
    label: str | None
    created_at: dt.datetime


class TransactionUpdateRequest(BaseModel):
    # V1: metadata only
    category: str | None = None
    subcategory: str | None = None
    label: str | None = None

    # V2-ready fields (present but not enabled yet)
    date: dt.date | None = None
    amount: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^-?\d+(\.\d{1,2})?$",
        description="V2: Signed amount as string, e.g. '-12.34' or '1000'",
    )
    kind: TransactionKind | None = None