import datetime as dt
from decimal import Decimal

import pytest

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind


def test_signed_money_allows_negative():
    sm = SignedMoney.from_str("-12.345", Currency.EUR)
    assert sm.amount == Decimal("-12.35")


def test_signed_money_allows_positive():
    sm = SignedMoney.from_str("100", Currency.EUR)
    assert sm.amount == Decimal("100.00")


def test_signed_money_allows_zero():
    sm = SignedMoney.from_str("0", Currency.EUR)
    assert sm.amount == Decimal("0.00")


def test_transaction_rejects_zero_amount():
    # ✅ La règle "pas de transaction à 0" vit dans Transaction.create (flux)
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="A",
            date=dt.date(2026, 1, 1),
            sequence=1,
            amount=SignedMoney.from_str("0", Currency.EUR),
            kind=TransactionKind.INCOME,
            category="Test",
        )


def test_signed_money_zero_constructor():
    eur = Currency.EUR
    z = SignedMoney.zero(eur)
    assert z.currency == eur
    assert z.amount == Decimal("0.00")


def test_signed_money_add_same_currency():
    eur = Currency.EUR

    a = SignedMoney.from_str("10.00", eur)
    b = SignedMoney.from_str("-3.50", eur)

    c = a + b

    assert c.currency == eur
    assert c.amount == Decimal("6.50")


def test_signed_money_add_quantizes_result():
    eur = Currency.EUR

    a = SignedMoney.from_str("0.10", eur)
    b = SignedMoney.from_str("0.20", eur)

    c = a + b
    assert c.amount == Decimal("0.30")


def test_signed_money_add_rejects_different_currency():
    eur = Currency.EUR
    usd = Currency("USD")

    a = SignedMoney.from_str("10.00", eur)
    b = SignedMoney.from_str("1.00", usd)

    with pytest.raises(ValueError):
        _ = a + b
