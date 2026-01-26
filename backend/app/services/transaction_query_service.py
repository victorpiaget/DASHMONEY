# app/services/transaction_query_service.py
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
from typing import Iterable, Literal, Sequence

from app.domain.transaction import Transaction, TransactionKind

SortBy = Literal["date", "amount", "kind", "category", "subcategory", "label"]
SortDir = Literal["asc", "desc"]


@dataclass(frozen=True)
class TransactionQuery:
    date_from: dt.date | None = None
    date_to: dt.date | None = None  # inclusif
    kinds: set[TransactionKind] | None = None
    categories: set[str] | None = None
    subcategories: set[str] | None = None
    q: str | None = None  # contains sur label (case-insensitive)
    sort_by: SortBy = "date"
    sort_dir: SortDir = "asc"


def apply_transaction_query(txs: Sequence[Transaction], q: TransactionQuery) -> list[Transaction]:
    out = list(txs)

    # -------- filters --------
    if q.date_from is not None:
        out = [t for t in out if t.date >= q.date_from]
    if q.date_to is not None:
        out = [t for t in out if t.date <= q.date_to]

    if q.kinds is not None:
        out = [t for t in out if t.kind in q.kinds]

    if q.categories is not None:
        out = [t for t in out if t.category in q.categories]

    if q.subcategories is not None:
        out = [t for t in out if t.subcategory is not None and t.subcategory in q.subcategories]

    if q.q is not None and q.q.strip():
        needle = q.q.strip().lower()
        out = [
            t for t in out
            if (t.label is not None and needle in t.label.lower())
        ]

    # -------- deterministic sort --------
    reverse = (q.sort_dir == "desc")

    def norm_str(s: str | None) -> str:
        return (s or "").casefold()

    def amount_value(t: Transaction) -> Decimal:
        # SignedMoney.amount est un Decimal -> parfait pour trier
        return t.amount.amount

    # clé primaire selon sort_by, puis tie-breakers (date, sequence)
    if q.sort_by == "date":
        key = lambda t: (t.date, t.sequence)
    elif q.sort_by == "amount":
        key = lambda t: (amount_value(t), t.date, t.sequence)
    elif q.sort_by == "kind":
        key = lambda t: (t.kind.value, t.date, t.sequence)
    elif q.sort_by == "category":
        key = lambda t: (norm_str(t.category), norm_str(t.subcategory), t.date, t.sequence)
    elif q.sort_by == "subcategory":
        key = lambda t: (norm_str(t.subcategory), norm_str(t.category), t.date, t.sequence)
    elif q.sort_by == "label":
        key = lambda t: (norm_str(t.label), t.date, t.sequence)
    else:
        # sécurité
        key = lambda t: (t.date, t.sequence)

    out.sort(key=key, reverse=reverse)
    return out
