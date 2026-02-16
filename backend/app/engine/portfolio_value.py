from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from app.domain.money import Currency
from app.domain.portfolio import Portfolio, PortfolioSnapshot
from app.domain.signed_money import SignedMoney


def _latest_snapshot_value(
    *,
    snapshots: list[PortfolioSnapshot],
    portfolio_id: UUID,
    at: dt.date | None,
) -> SignedMoney:
    """
    Valeur du dernier snapshot <= at (si at=None => dernier snapshot).
    Si aucun snapshot => 0.
    """
    relevant = [s for s in snapshots if s.portfolio_id == portfolio_id]
    if at is not None:
        relevant = [s for s in relevant if s.date <= at]

    if not relevant:
        # currency inconnue ici => géré par caller (il fixe la currency)
        raise KeyError("no snapshot")

    latest = max(relevant, key=lambda s: (s.date, str(s.id)))
    return SignedMoney(amount=latest.value.amount, currency=latest.value.currency)


def compute_portfolios_value(
    *,
    portfolios: list[Portfolio],
    snapshots: list[PortfolioSnapshot],
    at: dt.date | None,
    currency: Currency,
) -> SignedMoney:
    total = Decimal("0.00")

    for p in portfolios:
        if p.currency != currency:
            raise ValueError("Multiple currencies not supported yet (portfolio currency mismatch)")

        try:
            v = _latest_snapshot_value(snapshots=snapshots, portfolio_id=p.id, at=at)
            total += v.amount
        except KeyError:
            # pas de snapshot => 0
            continue

    return SignedMoney(amount=total, currency=currency)


def bucket_end_date(bucket: str, granularity: str, date_from: dt.date, date_to: dt.date) -> dt.date:
    """
    Reconstruit une date 'as_of' pour un bucket de tes timeseries.
    - daily: YYYY-MM-DD
    - weekly: YYYY-Www (ISO week)
    - monthly: YYYY-MM
    - yearly: YYYY
    """
    if granularity == "daily":
        d = dt.date.fromisoformat(bucket)
        return min(max(d, date_from), date_to)

    if granularity == "weekly":
        # bucket: "2026-W07"
        year_s, week_s = bucket.split("-W")
        y = int(year_s)
        w = int(week_s)
        # ISO: lundi=1 ... dimanche=7
        mon = dt.date.fromisocalendar(y, w, 1)
        sun = mon + dt.timedelta(days=6)
        d = min(sun, date_to)
        return max(d, date_from)

    if granularity == "monthly":
        y_s, m_s = bucket.split("-")
        y = int(y_s)
        m = int(m_s)
        # dernier jour du mois
        if m == 12:
            next_month = dt.date(y + 1, 1, 1)
        else:
            next_month = dt.date(y, m + 1, 1)
        last = next_month - dt.timedelta(days=1)
        d = min(last, date_to)
        return max(d, date_from)

    if granularity == "yearly":
        y = int(bucket)
        last = dt.date(y, 12, 31)
        d = min(last, date_to)
        return max(d, date_from)

    raise ValueError(f"unknown granularity '{granularity}'")