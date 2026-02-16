from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from typing import Literal

from app.domain.trade import Trade


SortBy = Literal["date", "quantity", "price", "fees", "side", "instrument_symbol", "label"]
SortDir = Literal["asc", "desc"]


@dataclass(frozen=True)
class TradeQuery:
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    sides: set[str] | None = None            # {"BUY","SELL"}
    symbols: set[str] | None = None          # {"BTC","AAPL"}
    q: str | None = None                     # recherche label ou symbol
    sort_by: SortBy = "date"
    sort_dir: SortDir = "asc"


def apply_trade_query(trades: list[Trade], query: TradeQuery) -> list[Trade]:
    out = trades

    # date range
    if query.date_from is not None:
        out = [t for t in out if t.date >= query.date_from]
    if query.date_to is not None:
        out = [t for t in out if t.date <= query.date_to]

    # sides
    if query.sides is not None:
        out = [t for t in out if t.side.value in query.sides]

    # symbols
    if query.symbols is not None:
        out = [t for t in out if t.instrument_symbol.upper() in query.symbols]

    # q search (label + symbol)
    if query.q is not None and query.q.strip():
        needle = query.q.strip().lower()
        def hay(t: Trade) -> str:
            parts = [t.instrument_symbol]
            if t.label:
                parts.append(t.label)
            return " ".join(parts).lower()

        out = [t for t in out if needle in hay(t)]

    # sorting
    reverse = query.sort_dir == "desc"

    def key(t: Trade):
        match query.sort_by:
            case "date":
                return (t.date, str(t.id))
            case "quantity":
                return (t.quantity, t.date, str(t.id))
            case "price":
                return (t.price, t.date, str(t.id))
            case "fees":
                return (t.fees, t.date, str(t.id))
            case "side":
                return (t.side.value, t.date, str(t.id))
            case "instrument_symbol":
                return (t.instrument_symbol.upper(), t.date, str(t.id))
            case "label":
                return ((t.label or "").lower(), t.date, str(t.id))
            case _:
                return (t.date, str(t.id))

    return sorted(out, key=key, reverse=reverse)