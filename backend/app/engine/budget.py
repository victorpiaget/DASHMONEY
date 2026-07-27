# app/engine/budget.py
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from app.domain.budget_envelope import BudgetEnvelope
from app.domain.category import CategoryNature
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


# ---------------------------------------------------------------------------
# Buckets par nature de catégorie (NEED / WANT / SAVING / uncategorized)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BucketTotals:
    needs: SignedMoney
    wants: SignedMoney
    savings: SignedMoney
    uncategorized: SignedMoney


def expense_buckets_by_nature(
    txs: list[Transaction],
    nature_map: dict[str, str | None],
    *,
    currency: Currency,
) -> BucketTotals:
    """Agrège les dépenses par bucket selon la nature de leur catégorie.

    `nature_map` : {category_name: "NEED"|"WANT"|"SAVING"|None}
    Une transaction dont la catégorie n'est pas dans `nature_map`, ou dont la
    nature est NULL, tombe dans `uncategorized`.
    Les TRANSFER et INCOME sont ignorés.
    """
    acc: dict[str, Decimal] = {
        "NEED": Decimal("0"),
        "WANT": Decimal("0"),
        "SAVING": Decimal("0"),
        "UNCAT": Decimal("0"),
    }

    for t in txs:
        if t.kind != TransactionKind.EXPENSE:
            continue
        nature = nature_map.get(t.category)
        if nature == "NEED":
            acc["NEED"] += t.amount.amount
        elif nature == "WANT":
            acc["WANT"] += t.amount.amount
        elif nature == "SAVING":
            acc["SAVING"] += t.amount.amount
        else:
            acc["UNCAT"] += t.amount.amount

    return BucketTotals(
        needs=SignedMoney.from_str(f"{acc['NEED']:.2f}", currency),
        wants=SignedMoney.from_str(f"{acc['WANT']:.2f}", currency),
        savings=SignedMoney.from_str(f"{acc['SAVING']:.2f}", currency),
        uncategorized=SignedMoney.from_str(f"{acc['UNCAT']:.2f}", currency),
    )


def expense_total_excluding_savings(buckets: BucketTotals, *, currency: Currency) -> SignedMoney:
    """Total dépenses au sens strict : NEED + WANT + UNCAT.
    Exclut SAVING qui est de l'épargne, pas une dépense."""
    total = (
        buckets.needs.amount
        + buckets.wants.amount
        + buckets.uncategorized.amount
    )
    return SignedMoney.from_str(f"{total:.2f}", currency)


def compute_savings(
    buckets: BucketTotals,
    income_actual: SignedMoney,
    *,
    currency: Currency,
) -> tuple[Money, Decimal]:
    """Retourne (savings_actual_positif, savings_rate) à partir des buckets.

    - savings_actual : valeur absolue du bucket SAVING (positive)
    - savings_rate : savings_actual / income_actual, arrondi à 4 décimales,
      0 si income_actual <= 0.
    """
    savings_pos = abs(buckets.savings.amount)
    savings_money = Money.from_str(f"{savings_pos:.2f}", currency)
    if income_actual.amount <= 0:
        return savings_money, Decimal("0.0000")
    rate = (savings_pos / income_actual.amount).quantize(Decimal("0.0001"))
    return savings_money, rate


# ---------------------------------------------------------------------------
# Flux budgétaires réels sur une période
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BudgetFlowIncomeSource:
    category: str
    subcategory: str | None
    amount: Money


@dataclass(frozen=True)
class BudgetFlowSubcategory:
    subcategory: str | None
    amount: Money


@dataclass(frozen=True)
class BudgetFlowExpenseCategory:
    category: str
    nature: CategoryNature | None
    amount: Money
    subcategories: tuple[BudgetFlowSubcategory, ...]


@dataclass(frozen=True)
class BudgetFlow:
    income_sources: tuple[BudgetFlowIncomeSource, ...]
    expense_categories: tuple[BudgetFlowExpenseCategory, ...]
    total_income: Money
    total_expenses: Money
    total_savings: Money
    total_outflows: Money
    balance: SignedMoney
    remaining: Money
    deficit: Money


def budget_flow(
    txs: list[Transaction],
    nature_map: dict[str, str | None],
    *,
    currency: Currency,
) -> BudgetFlow:
    """Agrège des flux réels positifs, prêts à être représentés en Sankey."""
    income_acc: dict[tuple[str, str | None], Decimal] = defaultdict(Decimal)
    expense_acc: dict[str, Decimal] = defaultdict(Decimal)
    subcategory_acc: dict[tuple[str, str | None], Decimal] = defaultdict(Decimal)

    for tx in txs:
        if tx.kind == TransactionKind.TRANSFER:
            continue
        if tx.kind == TransactionKind.INCOME:
            income_acc[(tx.category, tx.subcategory)] += tx.amount.amount
            continue

        amount = abs(tx.amount.amount)
        expense_acc[tx.category] += amount
        subcategory_acc[(tx.category, tx.subcategory)] += amount

    income_sources = tuple(
        BudgetFlowIncomeSource(
            category=category,
            subcategory=subcategory,
            amount=Money.from_str(f"{amount:.2f}", currency),
        )
        for (category, subcategory), amount in sorted(
            income_acc.items(),
            key=lambda item: (-item[1], item[0][0].casefold(), (item[0][1] or "").casefold()),
        )
    )

    nature_order = {
        CategoryNature.NEED: 0,
        CategoryNature.WANT: 1,
        CategoryNature.SAVING: 2,
        None: 3,
    }
    expense_categories: list[BudgetFlowExpenseCategory] = []
    for category, amount in expense_acc.items():
        raw_nature = nature_map.get(category)
        try:
            nature = CategoryNature(raw_nature) if raw_nature is not None else None
        except ValueError:
            nature = None

        subcategories = tuple(
            BudgetFlowSubcategory(
                subcategory=subcategory,
                amount=Money.from_str(f"{sub_amount:.2f}", currency),
            )
            for (sub_category, subcategory), sub_amount in sorted(
                subcategory_acc.items(),
                key=lambda item: (-item[1], (item[0][1] or "").casefold()),
            )
            if sub_category == category
        )
        expense_categories.append(
            BudgetFlowExpenseCategory(
                category=category,
                nature=nature,
                amount=Money.from_str(f"{amount:.2f}", currency),
                subcategories=subcategories,
            )
        )

    expense_categories.sort(
        key=lambda item: (
            nature_order[item.nature],
            -item.amount.amount,
            item.category.casefold(),
        )
    )

    total_income_value = sum(income_acc.values(), Decimal("0.00"))
    total_outflows_value = sum(expense_acc.values(), Decimal("0.00"))
    total_savings_value = sum(
        item.amount.amount
        for item in expense_categories
        if item.nature == CategoryNature.SAVING
    )
    total_expenses_value = total_outflows_value - total_savings_value
    balance_value = total_income_value - total_outflows_value

    return BudgetFlow(
        income_sources=income_sources,
        expense_categories=tuple(expense_categories),
        total_income=Money.from_str(f"{total_income_value:.2f}", currency),
        total_expenses=Money.from_str(f"{total_expenses_value:.2f}", currency),
        total_savings=Money.from_str(f"{total_savings_value:.2f}", currency),
        total_outflows=Money.from_str(f"{total_outflows_value:.2f}", currency),
        balance=SignedMoney.from_str(f"{balance_value:.2f}", currency),
        remaining=Money.from_str(f"{max(balance_value, Decimal('0.00')):.2f}", currency),
        deficit=Money.from_str(f"{max(-balance_value, Decimal('0.00')):.2f}", currency),
    )


# ---------------------------------------------------------------------------
# Médiane mensuelle par catégorie (pour auto-budget)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CategoryMedian:
    category: str
    subcategory: str | None
    kind: TransactionKind
    median_amount: Money
    occurrences: int  # nombre de mois où la (cat, sub, kind) a au moins 1 tx


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0.00")
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return ((s[mid - 1] + s[mid]) / 2).quantize(Decimal("0.01"))


def median_monthly_totals_by_category(
    txs: list[Transaction],
    *,
    months: list[tuple[int, int]],
    currency: Currency,
    min_occurrences: int = 2,
) -> list[CategoryMedian]:
    """Pour chaque (catégorie, sous-catégorie, kind), calcule la médiane des
    totaux mensuels absolus sur la fenêtre `months` (liste de tuples (year, month)).

    Ne renvoie que les couples ayant au moins `min_occurrences` mois avec au
    moins une transaction. Les TRANSFER sont ignorés.
    """
    months_set = set(months)
    monthly: dict[tuple[str, str | None, TransactionKind], dict[tuple[int, int], Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )

    for t in txs:
        if t.kind == TransactionKind.TRANSFER:
            continue
        key_month = (t.date.year, t.date.month)
        if key_month not in months_set:
            continue
        key = (t.category, t.subcategory, t.kind)
        monthly[key][key_month] += t.amount.amount

    results: list[CategoryMedian] = []
    for (cat, sub, kind), month_totals in monthly.items():
        occurrences = len(month_totals)
        if occurrences < min_occurrences:
            continue
        abs_values = [abs(v) for v in month_totals.values()]
        med = _median(abs_values)
        results.append(CategoryMedian(
            category=cat,
            subcategory=sub,
            kind=kind,
            median_amount=Money.from_str(f"{med:.2f}", currency),
            occurrences=occurrences,
        ))

    results.sort(key=lambda c: (
        0 if c.kind == TransactionKind.INCOME else 1,
        -c.median_amount.amount,
        c.category.casefold(),
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
