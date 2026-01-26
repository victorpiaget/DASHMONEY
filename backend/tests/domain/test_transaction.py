import pytest
from datetime import date
from uuid import UUID

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind


def usd(s: str) -> SignedMoney:
    return SignedMoney.from_str(s, Currency.USD)


def eur(s: str) -> SignedMoney:
    return SignedMoney.from_str(s, Currency.EUR)


def test_transaction_create_ok_income():
    tx = Transaction.create(
        account_id=" main ",
        date=date(2026, 1, 10),
        sequence=1,
        amount=eur("1000"),
        kind=TransactionKind.INCOME,
        category=" Revenus ",
        subcategory=" Salaire ",
        label=" Stage ",
    )

    assert isinstance(tx.id, UUID)
    assert tx.account_id == "main"
    assert tx.date == date(2026, 1, 10)
    assert tx.sequence == 1
    assert tx.amount.amount > 0
    assert tx.kind == TransactionKind.INCOME
    assert tx.category == "Revenus"
    assert tx.subcategory == "Salaire"
    assert tx.label == "Stage"
    assert tx.created_at.tzinfo is not None  # timezone-aware


def test_transaction_create_ok_expense():
    tx = Transaction.create(
        account_id="boursobank_main",
        date=date(2026, 1, 5),
        sequence=2,
        amount=eur("-650"),
        kind=TransactionKind.EXPENSE,
        category="Dépenses fixes",
        subcategory="Loyer",
    )
    assert tx.amount.amount < 0
    assert tx.kind == TransactionKind.EXPENSE


def test_transaction_sequence_must_be_ge_1():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=0,
            amount=eur("-1"),
            kind=TransactionKind.EXPENSE,
            category="X",
        )


def test_transaction_account_id_cannot_be_empty():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="   ",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("-1"),
            kind=TransactionKind.EXPENSE,
            category="X",
        )


def test_transaction_category_cannot_be_empty():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("-1"),
            kind=TransactionKind.EXPENSE,
            category="   ",
        )


def test_transaction_subcategory_if_provided_cannot_be_empty():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("-1"),
            kind=TransactionKind.EXPENSE,
            category="Dépenses",
            subcategory="   ",
        )


def test_transaction_label_if_provided_cannot_be_empty():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("-1"),
            kind=TransactionKind.EXPENSE,
            category="Dépenses",
            label="   ",
        )


def test_income_must_be_positive():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("-10"),
            kind=TransactionKind.INCOME,
            category="Revenus",
        )


def test_expense_must_be_negative():
    with pytest.raises(ValueError):
        Transaction.create(
            account_id="a",
            date=date(2026, 1, 1),
            sequence=1,
            amount=eur("10"),
            kind=TransactionKind.EXPENSE,
            category="Dépenses",
        )


def test_investment_allows_both_signs():
    buy = Transaction.create(
        account_id="a",
        date=date(2026, 1, 2),
        sequence=1,
        amount=usd("-200"),
        kind=TransactionKind.INVESTMENT,
        category="Investissements",
        subcategory="PEA",
    )
    sell = Transaction.create(
        account_id="a",
        date=date(2026, 1, 3),
        sequence=1,
        amount=usd("200"),
        kind=TransactionKind.INVESTMENT,
        category="Investissements",
        subcategory="PEA",
    )
    assert buy.amount.amount < 0
    assert sell.amount.amount > 0


def test_adjustment_allows_both_signs():
    plus = Transaction.create(
        account_id="a",
        date=date(2026, 1, 4),
        sequence=1,
        amount=eur("12.34"),
        kind=TransactionKind.ADJUSTMENT,
        category="Ajustements",
    )
    minus = Transaction.create(
        account_id="a",
        date=date(2026, 1, 5),
        sequence=1,
        amount=eur("-12.34"),
        kind=TransactionKind.ADJUSTMENT,
        category="Ajustements",
    )
    assert plus.amount.amount > 0
    assert minus.amount.amount < 0
