from __future__ import annotations

import datetime as dt

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.engine.budget import (
    totals_by_kind,
    expense_totals_by_category,
    monthly_totals_by_kind,
)


def _tx(date: dt.date, seq: int, amount: str, kind: TransactionKind, cat: str, sub: str | None = None):
    return Transaction.create(
        account_id="main",
        date=date,
        sequence=seq,
        amount=SignedMoney.from_str(amount, Currency.EUR),
        kind=kind,
        category=cat,
        subcategory=sub,
        label=None,
    )


def test_totals_by_kind_sums_correctly():
    txs = [
        _tx(dt.date(2026, 1, 1), 1, "1000.00", TransactionKind.INCOME, "Salaire"),
        _tx(dt.date(2026, 1, 2), 1, "-50.00", TransactionKind.EXPENSE, "Transport & mobilité", "Carburant"),
        _tx(dt.date(2026, 1, 3), 1, "-200.00", TransactionKind.INVESTMENT, "PEA"),
        _tx(dt.date(2026, 1, 4), 1, "-20.00", TransactionKind.EXPENSE, "Alimentation", "Courses"),
    ]

    out = totals_by_kind(txs, currency=Currency.EUR)
    got = {x.kind: x.total.amount for x in out}

    assert got[TransactionKind.INCOME] == SignedMoney.from_str("1000.00", Currency.EUR).amount
    assert got[TransactionKind.EXPENSE] == SignedMoney.from_str("-70.00", Currency.EUR).amount
    assert got[TransactionKind.INVESTMENT] == SignedMoney.from_str("-200.00", Currency.EUR).amount


def test_expense_totals_by_category_only_expense_and_grouped():
    txs = [
        _tx(dt.date(2026, 1, 1), 1, "-10.00", TransactionKind.EXPENSE, "Transport & mobilité", "Carburant"),
        _tx(dt.date(2026, 1, 2), 1, "-15.00", TransactionKind.EXPENSE, "Transport & mobilité", "Parking"),
        _tx(dt.date(2026, 1, 3), 1, "-30.00", TransactionKind.EXPENSE, "Alimentation", "Courses"),
        _tx(dt.date(2026, 1, 4), 1, "999.00", TransactionKind.INCOME, "Salaire"),  # doit être ignoré
    ]

    out = expense_totals_by_category(txs, currency=Currency.EUR)
    got = {x.category: x.total.amount for x in out}

    assert got["Transport & mobilité"] == SignedMoney.from_str("-25.00", Currency.EUR).amount
    assert got["Alimentation"] == SignedMoney.from_str("-30.00", Currency.EUR).amount
    assert "Salaire" not in got


def test_monthly_totals_by_kind_groups_by_month():
    txs = [
        _tx(dt.date(2026, 1, 1), 1, "-10.00", TransactionKind.EXPENSE, "Transport & mobilité", "Carburant"),
        _tx(dt.date(2026, 1, 15), 1, "-5.00", TransactionKind.EXPENSE, "Transport & mobilité", "Parking"),
        _tx(dt.date(2026, 2, 1), 1, "-20.00", TransactionKind.EXPENSE, "Alimentation", "Courses"),
        _tx(dt.date(2026, 2, 2), 1, "100.00", TransactionKind.INCOME, "Salaire"),
    ]

    out = monthly_totals_by_kind(txs, currency=Currency.EUR)

    # on crée une map (year, month, kind) -> total Decimal
    got = {(x.month.year, x.month.month, x.kind): x.total.amount for x in out}

    assert got[(2026, 1, TransactionKind.EXPENSE)] == SignedMoney.from_str("-15.00", Currency.EUR).amount
    assert got[(2026, 2, TransactionKind.EXPENSE)] == SignedMoney.from_str("-20.00", Currency.EUR).amount
    assert got[(2026, 2, TransactionKind.INCOME)] == SignedMoney.from_str("100.00", Currency.EUR).amount
