from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import Currency


@dataclass(frozen=True, slots=True)
class PricePoint:
    symbol: str
    day: dt.date               # UTC day
    price: Decimal
    currency: Currency
    source: str
    captured_at: dt.datetime   # UTC timestamp

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("price_point.symbol must be non-empty")
        if not isinstance(self.day, dt.date):
            raise ValueError("price_point.day must be a date")
        if not isinstance(self.price, Decimal):
            raise ValueError("price_point.price must be a Decimal")
        if not isinstance(self.currency, Currency):
            raise ValueError("price_point.currency must be a Currency")
        if not self.source or not self.source.strip():
            raise ValueError("price_point.source must be non-empty")
        if not isinstance(self.captured_at, dt.datetime):
            raise ValueError("price_point.captured_at must be a datetime")
        if self.captured_at.tzinfo is None:
            raise ValueError("price_point.captured_at must be timezone-aware (UTC)")
