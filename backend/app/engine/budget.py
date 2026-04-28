# app/engine/budget.py
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from app.domain.budget_envelope import BudgetEnvelope
from app.domain.money import Currency, Money
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


def income_totals_by_category(txs: list[Transaction], *, currency: Currency) -> list[CategoryTotal]:
    acc: dict[str, Decimal] = defaultdict(Decimal)
    for t in txs:
        if t.kind != TransactionKind.INCOME:
            continue
        acc[t.category] += t.amount.amount
    out = [
        CategoryTotal(category=c, total=SignedMoney.from_str(f"{v:.2f}", currency))
        for c, v in acc.items()
    ]
    out.sort(key=lambda x: (-x.total.amount, x.category.casefold()))
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


def income_totals_by_subcategory(txs: list[Transaction], *, currency: Currency) -> list[SubcategoryTotal]:
    acc: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for t in txs:
        if t.kind != TransactionKind.INCOME:
            continue
        if t.subcategory is None:
            continue
        acc[(t.category, t.subcategory)] += t.amount.amount
    out = [
        SubcategoryTotal(category=cat, subcategory=sub, total=SignedMoney.from_str(f"{v:.2f}", currency))
        for (cat, sub), v in acc.items()
    ]
    out.sort(key=lambda x: (-x.total.amount, x.category.casefold(), x.subcategory.casefold()))
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


# ---------------------------------------------------------------------------
# Budget prévisionnel — comparaison enveloppes vs réel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BudgetComparison:
    category: str
    subcategory: str | None
    kind: TransactionKind
    planned: Money
    actual: SignedMoney
    delta: SignedMoney
    percent: Decimal


@dataclass(frozen=True)
class BudgetSynthesis:
    total_income_planned: Money
    total_income_actual: SignedMoney
    total_expense_planned: Money
    total_expense_actual: SignedMoney
    net_planned: SignedMoney
    net_actual: SignedMoney


def budget_vs_actual(
    envelopes: list[BudgetEnvelope],
    transactions: list[Transaction],
    *,
    currency: Currency,
) -> list[BudgetComparison]:
    """Compare les enveloppes au réel.

    Inclut :
    - Les enveloppes avec ou sans transaction (actual = 0 si pas de transaction)
    - Les catégories avec des transactions mais sans enveloppe (planned = 0)
    Filtre les TRANSFER.
    """
    zero_signed = SignedMoney.from_str("0.00", currency)
    zero_money = Money.from_str("0.00", currency)

    # Agréger les transactions par (category, subcategory, kind)
    tx_acc: dict[tuple[str, str | None, TransactionKind], Decimal] = defaultdict(Decimal)
    for t in transactions:
        if t.kind == TransactionKind.TRANSFER:
            continue
        tx_acc[(t.category, t.subcategory, t.kind)] += t.amount.amount

    results: list[BudgetComparison] = []
    handled: set[tuple[str, str | None, TransactionKind]] = set()

    for env in envelopes:
        key = (env.category, env.subcategory, env.kind)
        actual_val = tx_acc.get(key, Decimal("0.00"))
        actual = SignedMoney.from_str(f"{actual_val:.2f}", currency)

        if env.kind == TransactionKind.EXPENSE:
            # delta positif = dépassement
            delta_val = abs(actual_val) - env.amount.amount
        else:
            # INCOME : delta positif = sur-performance
            delta_val = actual_val - env.amount.amount

        delta = SignedMoney.from_str(f"{delta_val:.2f}", currency)

        if env.amount.amount == Decimal("0"):
            percent = Decimal("0.00")
        else:
            percent = (abs(actual_val) / env.amount.amount * 100).quantize(Decimal("0.01"))

        results.append(BudgetComparison(
            category=env.category,
            subcategory=env.subcategory,
            kind=env.kind,
            planned=env.amount,
            actual=actual,
            delta=delta,
            percent=percent,
        ))
        handled.add(key)

    # Transactions sans enveloppe (non budgétées)
    for (cat, sub, kind), val in tx_acc.items():
        if kind == TransactionKind.TRANSFER:
            continue
        if (cat, sub, kind) in handled:
            continue
        actual = SignedMoney.from_str(f"{val:.2f}", currency)

        if kind == TransactionKind.EXPENSE:
            delta_val = abs(val)
        else:
            delta_val = val

        delta = SignedMoney.from_str(f"{delta_val:.2f}", currency)
        percent = Decimal("100.00") if val != Decimal("0") else Decimal("0.00")

        results.append(BudgetComparison(
            category=cat,
            subcategory=sub,
            kind=kind,
            planned=zero_money,
            actual=actual,
            delta=delta,
            percent=percent,
        ))

    # Tri : INCOME d'abord, puis par |actual| décroissant
    results.sort(key=lambda x: (
        0 if x.kind == TransactionKind.INCOME else 1,
        -abs(x.actual.amount),
    ))
    return results


def budget_synthesis(
    comparisons: list[BudgetComparison],
    *,
    currency: Currency,
) -> BudgetSynthesis:
    zero_signed = SignedMoney.from_str("0.00", currency)
    zero_money = Money.from_str("0.00", currency)

    inc_planned = Decimal("0.00")
    inc_actual = Decimal("0.00")
    exp_planned = Decimal("0.00")
    exp_actual = Decimal("0.00")

    for c in comparisons:
        if c.kind == TransactionKind.INCOME:
            inc_planned += c.planned.amount
            inc_actual += c.actual.amount
        elif c.kind == TransactionKind.EXPENSE:
            exp_planned += c.planned.amount
            exp_actual += c.actual.amount

    net_planned_val = inc_planned - exp_planned
    net_actual_val = inc_actual + exp_actual  # exp_actual est négatif

    return BudgetSynthesis(
        total_income_planned=Money.from_str(f"{inc_planned:.2f}", currency),
        total_income_actual=SignedMoney.from_str(f"{inc_actual:.2f}", currency),
        total_expense_planned=Money.from_str(f"{exp_planned:.2f}", currency),
        total_expense_actual=SignedMoney.from_str(f"{exp_actual:.2f}", currency),
        net_planned=SignedMoney.from_str(f"{net_planned_val:.2f}", currency),
        net_actual=SignedMoney.from_str(f"{net_actual_val:.2f}", currency),
    )
