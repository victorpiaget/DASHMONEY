import datetime as dt
from decimal import Decimal
import pytest

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.engine.running_balance import compute_running_balance_strict


def _tx(*, account_id: str, date: dt.date, sequence: int, amount: str, kind: TransactionKind, currency: Currency) -> Transaction:
    """
    Helper pour créer une transaction propre via la factory.
    """
    return Transaction.create(
        account_id=account_id,
        date=date,
        sequence=sequence,
        amount=SignedMoney.from_str(amount, currency),
        kind=kind,
        category="cat",
        subcategory=None,
        label=None,
    )


def test_running_balance_empty_list():
    assert compute_running_balance_strict([]) == []


def test_running_balance_single_transaction():
    eur = Currency("EUR")
    t1 = _tx(
        account_id="A",
        date=dt.date(2026, 1, 1),
        sequence=1,
        amount="100.00",
        kind=TransactionKind.INCOME,
        currency=eur,
    )

    out = compute_running_balance_strict([t1])

    assert len(out) == 1
    assert out[0].transaction == t1
    assert out[0].balance_after.amount == Decimal("100.00")
    assert out[0].balance_after.currency == eur


def test_running_balance_sorts_by_date_and_sequence():
    eur = Currency("EUR")

    # volontairement désordonné
    t1 = _tx(account_id="A", date=dt.date(2026, 1, 2), sequence=2, amount="-10.00", kind=TransactionKind.EXPENSE, currency=eur)
    t2 = _tx(account_id="A", date=dt.date(2026, 1, 2), sequence=1, amount="-20.00", kind=TransactionKind.EXPENSE, currency=eur)
    t3 = _tx(account_id="A", date=dt.date(2026, 1, 1), sequence=1, amount="100.00", kind=TransactionKind.INCOME, currency=eur)

    out = compute_running_balance_strict([t1, t2, t3])

    assert [(x.transaction.date, x.transaction.sequence) for x in out] == [
        (dt.date(2026, 1, 1), 1),
        (dt.date(2026, 1, 2), 1),
        (dt.date(2026, 1, 2), 2),
    ]

    assert out[0].balance_after.amount == Decimal("100.00")
    assert out[1].balance_after.amount == Decimal("80.00")
    assert out[2].balance_after.amount == Decimal("70.00")


def test_running_balance_can_return_to_zero():
    eur = Currency("EUR")

    t1 = _tx(account_id="A", date=dt.date(2026, 1, 1), sequence=1, amount="10.00", kind=TransactionKind.INCOME, currency=eur)
    t2 = _tx(account_id="A", date=dt.date(2026, 1, 1), sequence=2, amount="-10.00", kind=TransactionKind.EXPENSE, currency=eur)

    out = compute_running_balance_strict([t1, t2])

    assert out[1].balance_after.amount == Decimal("0.00")  # le solde doit pouvoir être zéro


def test_running_balance_rejects_mixed_account_ids():
    eur = Currency("EUR")

    t1 = _tx(account_id="A", date=dt.date(2026, 1, 1), sequence=1, amount="10.00", kind=TransactionKind.INCOME, currency=eur)
    t2 = _tx(account_id="B", date=dt.date(2026, 1, 1), sequence=1, amount="10.00", kind=TransactionKind.INCOME, currency=eur)

    with pytest.raises(ValueError):
        compute_running_balance_strict([t1, t2])


def test_running_balance_rejects_mixed_currency():
    eur = Currency("EUR")
    usd = Currency("USD")

    t1 = _tx(account_id="A", date=dt.date(2026, 1, 1), sequence=1, amount="10.00", kind=TransactionKind.INCOME, currency=eur)
    # même compte mais devise différente
    t2 = Transaction.create(
        account_id="A",
        date=dt.date(2026, 1, 1),
        sequence=2,
        amount=SignedMoney.from_str("5.00", usd),
        kind=TransactionKind.INCOME,
        category="cat",
        subcategory=None,
        label=None,
    )

    with pytest.raises(ValueError):
        compute_running_balance_strict([t1, t2])
