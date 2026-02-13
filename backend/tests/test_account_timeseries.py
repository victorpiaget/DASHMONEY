import datetime as dt
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.engine.account_timeseries import compute_timeseries
from app.engine.account_balance import compute_balance


def sm(value: str, currency: Currency = Currency.EUR) -> SignedMoney:
    # helper SignedMoney
    return SignedMoney(amount=Decimal(value), currency=currency)


def make_tx(
    *,
    account_id: str = "main",
    date: dt.date,
    amount: str,
    kind: TransactionKind,
    category: str = "cat",
    label: str = "lbl",
    sequence: int = 1,
):
    return Transaction.create(
        account_id=account_id,
        date=date,
        sequence=sequence,
        amount=sm(amount),
        kind=kind,
        category=category,
        subcategory=None,
        label=label,
        id=uuid4(),
        created_at=dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
    )

def test_timeseries_daily_excludes_transfer_from_income_expense_but_updates_balance():
    opening = sm("1000.00")

    d1 = dt.date(2026, 2, 10)
    d2 = dt.date(2026, 2, 11)

    txs = [
        # Day 1: income +200, expense -50, transfer -300 (should not count as expense bar)
        make_tx(date=d1, amount="200.00", kind=TransactionKind.INCOME, label="salary", sequence=1),
        make_tx(date=d1, amount="-50.00", kind=TransactionKind.EXPENSE, label="food", sequence=2),
        make_tx(date=d1, amount="-300.00", kind=TransactionKind.TRANSFER, label="to PEA", sequence=3),

        # Day 2: expense -10, transfer +300 (incoming), income +0 none
        make_tx(date=d2, amount="-10.00", kind=TransactionKind.EXPENSE, label="coffee", sequence=1),
        make_tx(date=d2, amount="300.00", kind=TransactionKind.TRANSFER, label="from main", sequence=2),
    ]

    points = compute_timeseries(
        opening_balance=opening,
        transactions=txs,
        date_from=d1,
        date_to=d2,
        granularity="daily",
    )

    assert [p["bucket"] for p in points] == ["2026-02-10", "2026-02-11"]

    # Day 1 bars: income=200, expense=50 (transfer ignored)
    p1 = points[0]
    assert p1["income"] == Decimal("200.00")
    assert p1["expense"] == Decimal("50.00")
    assert p1["net"] == Decimal("150.00")

    # Day 1 balance: 1000 + 200 - 50 - 300 = 850
    assert p1["balance_start"] == Decimal("1000.00")
    assert p1["balance_end"] == Decimal("850.00")

    # Day 2 bars: income=0, expense=10
    p2 = points[1]
    assert p2["income"] == Decimal("0")
    assert p2["expense"] == Decimal("10.00")
    assert p2["net"] == Decimal("-10.00")

    # Day 2 balance: 850 - 10 + 300 = 1140
    assert p2["balance_start"] == Decimal("850.00")
    assert p2["balance_end"] == Decimal("1140.00")


def test_compute_balance_at_date_includes_transfer_in_balance():
    opening = sm("1000.00")

    d1 = dt.date(2026, 2, 10)
    d2 = dt.date(2026, 2, 11)

    txs = [
        make_tx(date=d1, amount="200.00", kind=TransactionKind.INCOME, sequence=1),
        make_tx(date=d1, amount="-50.00", kind=TransactionKind.EXPENSE, sequence=2),
        make_tx(date=d1, amount="-300.00", kind=TransactionKind.TRANSFER, sequence=3),
        make_tx(date=d2, amount="-10.00", kind=TransactionKind.EXPENSE, sequence=1),
        make_tx(date=d2, amount="300.00", kind=TransactionKind.TRANSFER, sequence=2),
    ]

    # Balance at day1 end: 1000 + 200 - 50 - 300 = 850
    _, tx_sum1, bal1, n1 = compute_balance(opening_balance=opening, transactions=txs, at=d1)
    assert n1 == 3
    assert tx_sum1.amount == Decimal("-150.00")  # 200 - 50 - 300
    assert bal1.amount == Decimal("850.00")

    # Balance at day2 end: + (-10 + 300) => 1140
    _, tx_sum2, bal2, n2 = compute_balance(opening_balance=opening, transactions=txs, at=d2)
    assert n2 == 5
    assert tx_sum2.amount == Decimal("140.00")   # 200 - 50 - 300 - 10 + 300
    assert bal2.amount == Decimal("1140.00")