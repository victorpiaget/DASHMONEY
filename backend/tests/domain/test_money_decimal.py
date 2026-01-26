import pytest
from decimal import Decimal

from app.domain.money import Money, Currency


def test_money_from_str_quantizes_half_up():
    m = Money.from_str("12.345", Currency.EUR)
    assert m.amount == Decimal("12.35")


def test_money_accepts_comma_decimal():
    m = Money.from_str("12,345", Currency.EUR)
    assert m.amount == Decimal("12.35")


def test_money_rejects_negative():
    with pytest.raises(ValueError):
        Money.from_str("-0.01", Currency.EUR)


def test_money_empty_string_rejected():
    with pytest.raises(ValueError):
        Money.from_str("   ", Currency.EUR)
