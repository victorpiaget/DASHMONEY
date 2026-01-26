# app/engine/budget.py
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind


@dataclass(frozen=True)
class KindTotal:
    kind: TransactionKind
    total: SignedMoney


@dataclass(frozen=True)
class CategoryTotal:
    category: str
    total: SignedMoney


@dataclass(frozen=True)
class SubcategoryTotal:
    category: str
    subcategory: str
    total: SignedMoney


@dataclass(frozen=True)
class MonthKey:
    year: int
    month: int  # 1..12


@dataclass(frozen=True)
class MonthlyKindTotal:
    month: MonthKey
    kind: TransactionKind
    total: SignedMoney


# app/engine/budget.py (suite)

def _zero(currency: Currency) -> SignedMoney:
    return SignedMoney.from_str("0.00", currency)


def totals_by_kind(txs: list[Transaction], *, currency: Currency) -> list[KindTotal]:
    acc: dict[TransactionKind, Decimal] = defaultdict(Decimal)

    for t in txs:
        # currency déjà garantie par repo (strict)
        acc[t.kind] += t.amount.amount

    out = [
        KindTotal(kind=k, total=SignedMoney.from_str(f"{v:.2f}", currency))
        for k, v in acc.items()
    ]
    out.sort(key=lambda x: x.kind.value)  # stable
    return out


def expense_totals_by_category(txs: list[Transaction], *, currency: Currency) -> list[CategoryTotal]:
    acc: dict[str, Decimal] = defaultdict(Decimal)

    for t in txs:
        if t.kind != TransactionKind.EXPENSE:
            continue
        acc[t.category] += t.amount.amount  # négatif en général

    out = [
        CategoryTotal(category=c, total=SignedMoney.from_str(f"{v:.2f}", currency))
        for c, v in acc.items()
    ]
    # tri déterministe : plus grosse dépense (valeur la plus négative) d'abord ?
    # On reste descriptif : on trie par montant croissant (ex: -500, -20) => gros postes en haut
    out.sort(key=lambda x: (x.total.amount, x.category.casefold()))
    return out


def expense_totals_by_subcategory(txs: list[Transaction], *, currency: Currency) -> list[SubcategoryTotal]:
    acc: dict[tuple[str, str], Decimal] = defaultdict(Decimal)

    for t in txs:
        if t.kind != TransactionKind.EXPENSE:
            continue
        if t.subcategory is None:
            continue
        acc[(t.category, t.subcategory)] += t.amount.amount

    out = [
        SubcategoryTotal(category=cat, subcategory=sub, total=SignedMoney.from_str(f"{v:.2f}", currency))
        for (cat, sub), v in acc.items()
    ]
    out.sort(key=lambda x: (x.total.amount, x.category.casefold(), x.subcategory.casefold()))
    return out


def monthly_totals_by_kind(txs: list[Transaction], *, currency: Currency) -> list[MonthlyKindTotal]:
    acc: dict[tuple[int, int, TransactionKind], Decimal] = defaultdict(Decimal)

    for t in txs:
        acc[(t.date.year, t.date.month, t.kind)] += t.amount.amount

    out = [
        MonthlyKindTotal(
            month=MonthKey(year=y, month=m),
            kind=k,
            total=SignedMoney.from_str(f"{v:.2f}", currency),
        )
        for (y, m, k), v in acc.items()
    ]
    out.sort(key=lambda x: (x.month.year, x.month.month, x.kind.value))
    return out
