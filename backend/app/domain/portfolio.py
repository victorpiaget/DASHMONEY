from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.domain.money import Currency, Money


class PortfolioType(str, Enum):
    PEA = "PEA"
    CTO = "CTO"
    CRYPTO_EXCHANGE = "CRYPTO_EXCHANGE"  # ex Binance
    WALLET = "WALLET"                    # ex Ledger
    OTHER = "OTHER"


@dataclass(frozen=True)
class Portfolio:
    id: UUID
    name: str
    currency: Currency
    portfolio_type: PortfolioType
    opened_on: dt.date
    cash_account_id: str 

    @classmethod
    def create(
        cls,
        *,
        name: str,
        currency: Currency,
        portfolio_type: PortfolioType,
        opened_on: dt.date,
        id: Optional[UUID] = None,
    ) -> "Portfolio":
        pid = id or uuid4()
        cash_account_id = f"pt_{pid.hex}_cash"
        return cls(
            id=pid,
            name=name,
            currency=currency,
            portfolio_type=portfolio_type,
            opened_on=opened_on,
            cash_account_id=cash_account_id,
        )

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Portfolio name cannot be empty")
        if not isinstance(self.currency, Currency):
            raise ValueError("Invalid currency")
        if not isinstance(self.portfolio_type, PortfolioType):
            raise ValueError("Invalid portfolio_type")
        if not isinstance(self.opened_on, dt.date):
            raise ValueError("opened_on must be a date")
        if not self.cash_account_id or not self.cash_account_id.strip():
            raise ValueError("cash_account_id cannot be empty")


@dataclass(frozen=True)
class PortfolioSnapshot:
    id: UUID
    portfolio_id: UUID
    date: dt.date
    value: Money
    note: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        portfolio_id: UUID,
        date: dt.date,
        value: Money,
        note: Optional[str] = None,
        id: Optional[UUID] = None,
    ) -> "PortfolioSnapshot":
        sid = id or uuid4()
        return cls(
            id=sid,
            portfolio_id=portfolio_id,
            date=date,
            value=value,
            note=note.strip() if isinstance(note, str) and note.strip() else None,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.portfolio_id, UUID):
            raise ValueError("portfolio_id must be a UUID")
        if not isinstance(self.date, dt.date):
            raise ValueError("date must be a date")
        if not isinstance(self.value, Money):
            raise ValueError("value must be a Money")