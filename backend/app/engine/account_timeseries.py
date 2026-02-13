from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind


Granularity = str  # "daily"|"weekly"|"monthly"|"yearly"


def pick_granularity(date_from: dt.date, date_to: dt.date) -> Granularity:
    days = (date_to - date_from).days + 1
    if days <= 60:
        return "daily"
    if days <= 548:   # ~18 mois
        return "weekly"
    if days <= 2920:  # ~8 ans
        return "monthly"
    return "yearly"


def _signed_decimal(tx: Transaction) -> Decimal:
    # Chez nous le signe est porté par tx.amount.amount (INCOME > 0, EXPENSE < 0, TRANSFER +/-)
    return tx.amount.amount


def _income_expense_decimals(tx: Transaction) -> tuple[Decimal, Decimal]:
    """
    Pour le graphe: INCOME et EXPENSE sont POSITIFS.
    TRANSFER est ignoré (0,0) pour ne pas biaiser les barres.
    """
    amt = abs(tx.amount.amount)

    if tx.kind == TransactionKind.INCOME:
        return amt, Decimal("0")

    if tx.kind == TransactionKind.EXPENSE:
        return Decimal("0"), amt

    # TRANSFER (et tout autre kind futur) : ignoré pour income/expense
    return Decimal("0"), Decimal("0")


def _bucket_label(g: Granularity, d: dt.date) -> str:
    if g == "daily":
        return d.isoformat()
    if g == "weekly":
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year:04d}-W{iso_week:02d}"
    if g == "monthly":
        return f"{d.year:04d}-{d.month:02d}"
    if g == "yearly":
        return f"{d.year:04d}"
    raise ValueError(f"unknown granularity '{g}'")


def compute_timeseries(
    *,
    opening_balance: SignedMoney,
    transactions: list[Transaction],
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity,
) -> list[dict]:
    """
    Returns points (dict) ordered by bucket:
    {bucket, income, expense, net, balance_end} with Decimal values (not formatted).
    """
    if date_from > date_to:
        raise ValueError("date_from must be <= date_to")

    # Filter txs that affect output range + txs before range for initial balance
    txs_in_range = [t for t in transactions if date_from <= t.date <= date_to]
    txs_before = [t for t in transactions if t.date < date_from]

    # initial balance at date_from
    balance = opening_balance.amount + sum((_signed_decimal(t) for t in txs_before), Decimal("0"))

    # Group txs by bucket label
    buckets: dict[str, dict] = {}
    for t in txs_in_range:
        b = _bucket_label(granularity, t.date)
        if b not in buckets:
            buckets[b] = {"income": Decimal("0"), "expense": Decimal("0"), "signed_sum": Decimal("0")}
        inc, exp = _income_expense_decimals(t)
        buckets[b]["income"] += inc
        buckets[b]["expense"] += exp
        buckets[b]["signed_sum"] += _signed_decimal(t)

    # We must output buckets in chronological order, including empty buckets.
    # We'll iterate dates and record bucket transitions.
    points: list[dict] = []
    seen: set[str] = set()

    cur = date_from
    last_bucket: str | None = None

    def flush_bucket(bucket: str) -> None:
        nonlocal balance
        data = buckets.get(bucket, {"income": Decimal("0"), "expense": Decimal("0"), "signed_sum": Decimal("0")})

        balance_start = balance
        balance_end = balance + data["signed_sum"]
        balance = balance_end  # update state

        income = data["income"]
        expense = data["expense"]
        net = income - expense

        points.append(
            {
                "bucket": bucket,
                "income": income,
                "expense": expense,
                "net": net,
                "balance_start": balance_start,  # NEW
                "balance_end": balance_end,
            }
        )

    while cur <= date_to:
        b = _bucket_label(granularity, cur)
        if last_bucket is None:
            last_bucket = b

        if b != last_bucket:
            if last_bucket not in seen:
                flush_bucket(last_bucket)
                seen.add(last_bucket)
            last_bucket = b

        # advance
        cur += dt.timedelta(days=1)

    # flush last
    if last_bucket is not None and last_bucket not in seen:
        flush_bucket(last_bucket)

    return points