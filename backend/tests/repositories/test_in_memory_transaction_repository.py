import datetime as dt
import pytest

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.repositories.in_memory_transaction_repository import InMemoryTransactionRepository


def eur(s: str) -> SignedMoney:
    return SignedMoney.from_str(s, Currency.EUR)


def make_tx(
    *,
    account_id: str,
    date: dt.date,
    sequence: int,
    amount: str,
    kind: TransactionKind,
    category: str = "Cat",
) -> Transaction:
    return Transaction.create(
        account_id=account_id,
        date=date,
        sequence=sequence,
        amount=eur(amount),
        kind=kind,
        category=category,
    )


def test_add_and_get():
    repo = InMemoryTransactionRepository()
    tx = make_tx(
        account_id="a",
        date=dt.date(2026, 1, 1),
        sequence=1,
        amount="10",
        kind=TransactionKind.INCOME,
    )

    repo.add(tx)
    assert repo.get(tx.id) == tx


def test_add_duplicate_id_raises():
    repo = InMemoryTransactionRepository()
    tx = make_tx(
        account_id="a",
        date=dt.date(2026, 1, 1),
        sequence=1,
        amount="10",
        kind=TransactionKind.INCOME,
    )
    repo.add(tx)

    with pytest.raises(ValueError):
        repo.add(tx)  # même id


def test_list_sorts_by_date_then_sequence():
    repo = InMemoryTransactionRepository()

    tx2 = make_tx(
        account_id="a",
        date=dt.date(2026, 1, 2),
        sequence=1,
        amount="10",
        kind=TransactionKind.INCOME,
    )
    tx1 = make_tx(
        account_id="a",
        date=dt.date(2026, 1, 1),
        sequence=2,
        amount="-1",
        kind=TransactionKind.EXPENSE,
    )
    tx0 = make_tx(
        account_id="a",
        date=dt.date(2026, 1, 1),
        sequence=1,
        amount="5",
        kind=TransactionKind.INCOME,
    )

    repo.add(tx2)
    repo.add(tx1)
    repo.add(tx0)

    listed = repo.list("a")
    assert [t.sequence for t in listed if t.date == dt.date(2026, 1, 1)] == [1, 2]
    assert listed[0].date == dt.date(2026, 1, 1)
    assert listed[-1].date == dt.date(2026, 1, 2)


def test_list_filters_by_account_id():
    repo = InMemoryTransactionRepository()
    repo.add(make_tx(account_id="a", date=dt.date(2026, 1, 1), sequence=1, amount="10", kind=TransactionKind.INCOME))
    repo.add(make_tx(account_id="b", date=dt.date(2026, 1, 1), sequence=1, amount="10", kind=TransactionKind.INCOME))

    listed_a = repo.list("a")
    assert len(listed_a) == 1
    assert listed_a[0].account_id == "a"


def test_next_sequence_returns_1_if_none_that_day():
    repo = InMemoryTransactionRepository()
    seq = repo.next_sequence("a", dt.date(2026, 1, 1))
    assert seq == 1


def test_next_sequence_increments_for_same_day_and_account():
    repo = InMemoryTransactionRepository()
    repo.add(make_tx(account_id="a", date=dt.date(2026, 1, 1), sequence=1, amount="10", kind=TransactionKind.INCOME))
    repo.add(make_tx(account_id="a", date=dt.date(2026, 1, 1), sequence=2, amount="-1", kind=TransactionKind.EXPENSE))

    seq = repo.next_sequence("a", dt.date(2026, 1, 1))
    assert seq == 3


def test_next_sequence_independent_per_account_and_day():
    repo = InMemoryTransactionRepository()
    repo.add(make_tx(account_id="a", date=dt.date(2026, 1, 1), sequence=5, amount="10", kind=TransactionKind.INCOME))
    repo.add(make_tx(account_id="b", date=dt.date(2026, 1, 1), sequence=2, amount="10", kind=TransactionKind.INCOME))
    repo.add(make_tx(account_id="a", date=dt.date(2026, 1, 2), sequence=7, amount="10", kind=TransactionKind.INCOME))

    assert repo.next_sequence("a", dt.date(2026, 1, 1)) == 6
    assert repo.next_sequence("b", dt.date(2026, 1, 1)) == 3
    assert repo.next_sequence("a", dt.date(2026, 1, 2)) == 8
