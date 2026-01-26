import datetime as dt
from app.domain.signed_money import SignedMoney
from app.domain.money import Currency
from app.domain.transaction import Transaction, TransactionKind
from app.services.transaction_query_service import TransactionQuery, apply_transaction_query

def _tx(account_id: str, date: dt.date, seq: int, amount: str, kind: TransactionKind, cat: str, sub: str | None, label: str | None):
    return Transaction.create(
        account_id=account_id,
        date=date,
        sequence=seq,
        amount=SignedMoney.from_str(amount, Currency.EUR),
        kind=kind,
        category=cat,
        subcategory=sub,
        label=label,
    )

def test_sort_amount_desc_with_stable_tiebreaker():
    d = dt.date(2026, 1, 10)
    tx1 = _tx("main", d, 1, "-10.00", TransactionKind.EXPENSE, "Transport", "Carburant", "A")
    tx2 = _tx("main", d, 2, "-10.00", TransactionKind.EXPENSE, "Transport", "Carburant", "B")
    tx3 = _tx("main", d, 3, "-20.00", TransactionKind.EXPENSE, "Transport", "Carburant", "C")

    q = TransactionQuery(sort_by="amount", sort_dir="desc")
    out = apply_transaction_query([tx1, tx2, tx3], q)

    # desc sur amount : -10 > -20
    # et tie-breaker date/sequence pour -10 identiques => seq 1 puis 2
    assert [t.sequence for t in out] == [1, 2, 3]

def test_filter_by_date_range_inclusive():
    t1 = _tx("main", dt.date(2026, 1, 1), 1, "-5.00", TransactionKind.EXPENSE, "Food", None, None)
    t2 = _tx("main", dt.date(2026, 1, 15), 1, "-6.00", TransactionKind.EXPENSE, "Food", None, None)
    t3 = _tx("main", dt.date(2026, 2, 1), 1, "-7.00", TransactionKind.EXPENSE, "Food", None, None)

    q = TransactionQuery(date_from=dt.date(2026, 1, 1), date_to=dt.date(2026, 1, 15))
    out = apply_transaction_query([t1, t2, t3], q)
    assert [t.date for t in out] == [dt.date(2026, 1, 1), dt.date(2026, 1, 15)]

def test_filter_category_and_subcategory():
    a = _tx("main", dt.date(2026, 1, 2), 1, "-10.00", TransactionKind.EXPENSE, "Transport & mobilité", "Carburant", None)
    b = _tx("main", dt.date(2026, 1, 2), 2, "-10.00", TransactionKind.EXPENSE, "Transport & mobilité", "Assurance", None)
    c = _tx("main", dt.date(2026, 1, 2), 3, "-10.00", TransactionKind.EXPENSE, "Alimentation", "Courses", None)

    q = TransactionQuery(
        categories={"Transport & mobilité"},
        subcategories={"Carburant"},
    )
    out = apply_transaction_query([a, b, c], q)
    assert len(out) == 1
    assert out[0].subcategory == "Carburant"
