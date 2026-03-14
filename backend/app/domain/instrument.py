from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

( # noqa: E701
)
from app.domain.money import Currency


class InstrumentKind(str, Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    CRYPTO = "CRYPTO"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str          # ex: "BTC", "AAPL", "FR0013412020"
    kind: InstrumentKind
    currency: Currency   # devise de cotation / pricing
    name: str = ""       # nom d'affichage, ex: "Amundi PEA MSCI Emerging"
    ticker: str = ""     # ticker Yahoo Finance, ex: "PAEEM.PA", "BTC-EUR"

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("instrument.symbol must be non-empty")
        if not isinstance(self.kind, InstrumentKind):
            raise ValueError("instrument.kind invalid")
        if not isinstance(self.currency, Currency):
            raise ValueError("instrument.currency must be a Currency")