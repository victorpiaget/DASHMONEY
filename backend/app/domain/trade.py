from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import datetime as dt
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.money import Currency


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Trade:
    id: UUID
    portfolio_id: UUID
    date: dt.date
    side: TradeSide
    instrument_symbol: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    currency: Currency
    label: str | None
    linked_cash_tx_id: UUID | None  # transaction miroir dans le compte passerelle

    @classmethod
    def create(
        cls,
        *,
        portfolio_id: UUID,
        date: dt.date,
        side: TradeSide,
        instrument_symbol: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal,
        currency: Currency,
        label: str | None = None,
        linked_cash_tx_id: UUID | None = None,
        id: UUID | None = None,
    ) -> "Trade":
        tid = id or uuid4()
        return cls(
            id=tid,
            portfolio_id=portfolio_id,
            date=date,
            side=side,
            instrument_symbol=instrument_symbol.strip(),
            quantity=quantity,
            price=price,
            fees=fees,
            currency=currency,
            label=label.strip() if isinstance(label, str) and label.strip() else None,
            linked_cash_tx_id=linked_cash_tx_id,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.portfolio_id, UUID):
            raise ValueError("trade.portfolio_id must be UUID")
        if not isinstance(self.id, UUID):
            raise ValueError("trade.id must be UUID")
        if not isinstance(self.date, dt.date):
            raise ValueError("trade.date must be a date")
        if not isinstance(self.side, TradeSide):
            raise ValueError("trade.side invalid")
        if not self.instrument_symbol:
            raise ValueError("trade.instrument_symbol must be non-empty")
        if self.quantity <= 0:
            raise ValueError("trade.quantity must be > 0")
        if self.price <= 0:
            raise ValueError("trade.price must be > 0")
        if self.fees < 0:
            raise ValueError("trade.fees must be >= 0")
        if not isinstance(self.currency, Currency):
            raise ValueError("trade.currency must be a Currency")