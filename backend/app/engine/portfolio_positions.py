from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from app.domain.trade import Trade, TradeSide


def compute_positions(
    *,
    trades: list[Trade],
    portfolio_id: UUID,
    as_of: dt.date | None,
) -> dict[str, Decimal]:
    """
    Returns {instrument_symbol: quantity} as of date (inclusive).
    """
    pos: dict[str, Decimal] = {}

    for t in trades:
        if t.portfolio_id != portfolio_id:
            continue
        if as_of is not None and t.date > as_of:
            continue

        sym = t.instrument_symbol.upper()
        pos.setdefault(sym, Decimal("0"))

        if t.side == TradeSide.BUY:
            pos[sym] += t.quantity
        else:
            pos[sym] -= t.quantity

    # cleanup ~0
    to_del = [k for k, v in pos.items() if v == 0]
    for k in to_del:
        pos.pop(k, None)

    return pos