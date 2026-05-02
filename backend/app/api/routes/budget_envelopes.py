from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import (
    get_account_repo,
    get_budget_envelope_repo,
    get_category_repo,
    get_request_context,
    get_tx_repo,
    get_write_context,
)
from app.api.schemas.budget_envelopes import (
    BudgetAutoBudgetResponse,
    BudgetAutoBudgetSuggestion,
    BudgetBucketsResponse,
    BudgetCategoriesResponse,
    BudgetCategoryItem,
    BudgetComparisonFullResponse,
    BudgetComparisonResponse,
    BudgetEnvelopeRequest,
    BudgetEnvelopeResponse,
    BudgetHistoryMonthResponse,
    BudgetHistoryResponse,
    BudgetSynthesisResponse,
)
from app.domain.budget_envelope import BudgetEnvelope
from app.domain.money import Currency, Money
from app.domain.transaction import TransactionKind
from app.engine.budget import (
    budget_synthesis,
    budget_vs_actual,
    compute_savings,
    expense_buckets_by_nature,
    expense_total_excluding_savings,
    median_monthly_totals_by_category,
)
from app.identity.request_context import RequestContext
from app.db import new_session
from app.repositories.sql_transaction_repository import TransactionRow
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/budget", tags=["budget"])


def _envelope_to_response(env: BudgetEnvelope, *, profile_id: str) -> BudgetEnvelopeResponse:
    return BudgetEnvelopeResponse(
        id=str(env.id),
        category=env.category,
        subcategory=env.subcategory,
        kind=env.kind.value,
        amount=f"{env.amount.amount:.2f}",
        currency=env.amount.currency.value,
        profile_id=profile_id,
    )


@router.get("/envelopes", response_model=list[BudgetEnvelopeResponse])
def list_envelopes(
    ctx: RequestContext = Depends(get_request_context),
) -> list[BudgetEnvelopeResponse]:
    repo = get_budget_envelope_repo()
    envelopes = repo.list(profile_id=ctx.profile_id)
    return [_envelope_to_response(e, profile_id=ctx.profile_id) for e in envelopes]


@router.put("/envelopes", response_model=BudgetEnvelopeResponse)
def upsert_envelope(
    req: BudgetEnvelopeRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> BudgetEnvelopeResponse:
    try:
        kind = TransactionKind(req.kind)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid kind: {req.kind!r}. Must be INCOME or EXPENSE.")

    try:
        amount = Money.from_str(req.amount, Currency.EUR)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        envelope = BudgetEnvelope.create(
            category=req.category,
            subcategory=req.subcategory,
            kind=kind,
            amount=amount,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = get_budget_envelope_repo()
    saved = repo.upsert(envelope, profile_id=ctx.profile_id)
    return _envelope_to_response(saved, profile_id=ctx.profile_id)


@router.delete("/envelopes/{envelope_id}", status_code=204)
def delete_envelope(
    envelope_id: str,
    ctx: RequestContext = Depends(get_write_context),
) -> Response:
    repo = get_budget_envelope_repo()
    deleted = repo.delete(envelope_id, profile_id=ctx.profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Envelope not found")
    return Response(status_code=204)


@router.get("/comparison", response_model=BudgetComparisonFullResponse)
def budget_comparison(
    month: str = Query(..., description="Format YYYY-MM, ex: 2026-03"),
    ctx: RequestContext = Depends(get_request_context),
) -> BudgetComparisonFullResponse:
    try:
        year, m = month.split("-")
        year_int, month_int = int(year), int(m)
        if not (1 <= month_int <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="month must be in YYYY-MM format")

    date_from = dt.date(year_int, month_int, 1)
    if month_int == 12:
        date_to = dt.date(year_int + 1, 1, 1) - dt.timedelta(days=1)
    else:
        date_to = dt.date(year_int, month_int + 1, 1) - dt.timedelta(days=1)

    currency = Currency.EUR

    envelope_repo = get_budget_envelope_repo()
    envelopes = envelope_repo.list(profile_id=ctx.profile_id)

    tx_repo = get_tx_repo()
    all_txs = tx_repo.list(profile_id=ctx.profile_id)
    month_txs = [t for t in all_txs if date_from <= t.date <= date_to]

    comparisons = budget_vs_actual(envelopes, month_txs, currency=currency)
    synthesis = budget_synthesis(comparisons, currency=currency)

    nature_map = get_category_repo().list_natures(profile_id=ctx.profile_id)
    buckets = expense_buckets_by_nature(month_txs, nature_map, currency=currency)
    total_expenses = expense_total_excluding_savings(buckets, currency=currency)
    savings_actual, savings_rate = compute_savings(
        buckets, synthesis.total_income_actual, currency=currency,
    )

    return BudgetComparisonFullResponse(
        month=month,
        currency=currency.value,
        synthesis=BudgetSynthesisResponse(
            total_income_planned=f"{synthesis.total_income_planned.amount:.2f}",
            total_income_actual=f"{synthesis.total_income_actual.amount:.2f}",
            total_expense_planned=f"{synthesis.total_expense_planned.amount:.2f}",
            total_expense_actual=f"{synthesis.total_expense_actual.amount:.2f}",
            net_planned=f"{synthesis.net_planned.amount:.2f}",
            net_actual=f"{synthesis.net_actual.amount:.2f}",
            savings_actual=f"{savings_actual.amount:.2f}",
            savings_rate=f"{savings_rate:.4f}",
        ),
        comparisons=[
            BudgetComparisonResponse(
                category=c.category,
                subcategory=c.subcategory,
                kind=c.kind.value,
                planned=f"{c.planned.amount:.2f}",
                actual=f"{c.actual.amount:.2f}",
                delta=f"{c.delta.amount:.2f}",
                percent=f"{c.percent:.2f}",
            )
            for c in comparisons
        ],
        buckets=BudgetBucketsResponse(
            needs=f"{buckets.needs.amount:.2f}",
            wants=f"{buckets.wants.amount:.2f}",
            savings=f"{buckets.savings.amount:.2f}",
            uncategorized=f"{buckets.uncategorized.amount:.2f}",
            total_expenses=f"{total_expenses.amount:.2f}",
        ),
        profile_id=ctx.profile_id,
    )


@router.get("/history", response_model=BudgetHistoryResponse)
def budget_history(
    months: int = Query(default=6, ge=1, le=24),
    ctx: RequestContext = Depends(get_request_context),
) -> BudgetHistoryResponse:
    currency = Currency.EUR
    today = dt.date.today()

    envelope_repo = get_budget_envelope_repo()
    envelopes = envelope_repo.list(profile_id=ctx.profile_id)

    tx_repo = get_tx_repo()
    all_txs = tx_repo.list(profile_id=ctx.profile_id)

    nature_map = get_category_repo().list_natures(profile_id=ctx.profile_id)

    result_months: list[BudgetHistoryMonthResponse] = []

    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        date_from = dt.date(year, month, 1)
        if month == 12:
            date_to = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
        else:
            date_to = dt.date(year, month + 1, 1) - dt.timedelta(days=1)

        month_txs = [t for t in all_txs if date_from <= t.date <= date_to]
        comparisons = budget_vs_actual(envelopes, month_txs, currency=currency)
        synthesis = budget_synthesis(comparisons, currency=currency)

        buckets = expense_buckets_by_nature(month_txs, nature_map, currency=currency)
        savings_actual, savings_rate = compute_savings(
            buckets, synthesis.total_income_actual, currency=currency,
        )

        result_months.append(BudgetHistoryMonthResponse(
            month=f"{year}-{month:02d}",
            income_actual=f"{synthesis.total_income_actual.amount:.2f}",
            expense_actual=f"{synthesis.total_expense_actual.amount:.2f}",
            net_actual=f"{synthesis.net_actual.amount:.2f}",
            income_planned=f"{synthesis.total_income_planned.amount:.2f}",
            expense_planned=f"{synthesis.total_expense_planned.amount:.2f}",
            savings_actual=f"{savings_actual.amount:.2f}",
            savings_rate=f"{savings_rate:.4f}",
        ))

    return BudgetHistoryResponse(
        months=result_months,
        currency=currency.value,
        profile_id=ctx.profile_id,
    )


@router.get("/categories", response_model=BudgetCategoriesResponse)
def budget_categories(
    ctx: RequestContext = Depends(get_request_context),
) -> BudgetCategoriesResponse:
    from collections import defaultdict

    with new_session() as s:
        rows = s.execute(
            select(TransactionRow.category, TransactionRow.subcategory, TransactionRow.kind)
            .where(TransactionRow.profile_id == ctx.profile_id)
            .distinct()
        ).all()

    income_acc: dict[str, set[str]] = defaultdict(set)
    expense_acc: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        cat, sub, kind = row.category, row.subcategory, row.kind
        if kind == TransactionKind.TRANSFER.value:
            continue
        if kind == TransactionKind.INCOME.value:
            if sub:
                income_acc[cat].add(sub)
            else:
                income_acc.setdefault(cat, set())
        elif kind == TransactionKind.EXPENSE.value:
            if sub:
                expense_acc[cat].add(sub)
            else:
                expense_acc.setdefault(cat, set())

    nature_map = get_category_repo().list_natures(profile_id=ctx.profile_id)

    income = [
        BudgetCategoryItem(category=cat, subcategories=sorted(subs), nature=nature_map.get(cat))
        for cat, subs in sorted(income_acc.items())
    ]
    expense = [
        BudgetCategoryItem(category=cat, subcategories=sorted(subs), nature=nature_map.get(cat))
        for cat, subs in sorted(expense_acc.items())
    ]

    return BudgetCategoriesResponse(income=income, expense=expense)


@router.get("/auto-budget", response_model=BudgetAutoBudgetResponse)
def budget_auto_budget(
    months: int = Query(default=3, ge=1, le=12),
    ctx: RequestContext = Depends(get_request_context),
) -> BudgetAutoBudgetResponse:
    """Suggestions d'enveloppes calculées sur la médiane des N derniers mois pleins.

    Le mois courant est exclu (incomplet). Renvoie uniquement les couples
    (catégorie, sous-catégorie, kind) ayant au moins 2 mois avec transactions.
    """
    currency = Currency.EUR
    today = dt.date.today()

    months_window: list[tuple[int, int]] = []
    for i in range(1, months + 1):
        year = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            year -= 1
        months_window.append((year, m))

    if not months_window:
        return BudgetAutoBudgetResponse(
            based_on_months=0,
            from_month=today.strftime("%Y-%m"),
            to_month=today.strftime("%Y-%m"),
            suggestions=[],
            currency=currency.value,
            profile_id=ctx.profile_id,
        )

    from_y, from_m = min(months_window)
    to_y, to_m = max(months_window)

    tx_repo = get_tx_repo()
    all_txs = tx_repo.list(profile_id=ctx.profile_id)

    medians = median_monthly_totals_by_category(
        all_txs, months=months_window, currency=currency, min_occurrences=2,
    )

    nature_map = get_category_repo().list_natures(profile_id=ctx.profile_id)

    suggestions = [
        BudgetAutoBudgetSuggestion(
            category=m.category,
            subcategory=m.subcategory,
            kind=m.kind.value,
            nature=nature_map.get(m.category),
            median_amount=f"{m.median_amount.amount:.2f}",
            occurrences=m.occurrences,
        )
        for m in medians
    ]

    return BudgetAutoBudgetResponse(
        based_on_months=len(months_window),
        from_month=f"{from_y}-{from_m:02d}",
        to_month=f"{to_y}-{to_m:02d}",
        suggestions=suggestions,
        currency=currency.value,
        profile_id=ctx.profile_id,
    )
