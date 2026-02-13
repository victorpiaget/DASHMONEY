from __future__ import annotations

import datetime as dt
import logging
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_account_repo, get_tx_repo
from app.engine.budget import (
    totals_by_kind,
    expense_totals_by_category,
    expense_totals_by_subcategory,
    monthly_totals_by_kind,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["budgets"])


@router.get("/{account_id}/budget-summary")
def budget_summary(
    account_id: str,
    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),
):
    try:
        acc = get_account_repo().get_account(account_id)
        txs = get_tx_repo().list(account_id=acc.id)

        if date_from is not None:
            txs = [t for t in txs if t.date >= date_from]
        if date_to is not None:
            txs = [t for t in txs if t.date <= date_to]

        kb = totals_by_kind(txs, currency=acc.currency)
        by_cat = expense_totals_by_category(txs, currency=acc.currency)
        by_sub = expense_totals_by_subcategory(txs, currency=acc.currency)
        by_month_kind = monthly_totals_by_kind(txs, currency=acc.currency)

        return {
            "account_id": acc.id,
            "currency": acc.currency.value,
            "range": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            "totals_by_kind": [{"kind": x.kind.value, "total": f"{x.total.amount:.2f}"} for x in kb],
            "expense_by_category": [{"category": x.category, "total": f"{x.total.amount:.2f}"} for x in by_cat],
            "expense_by_subcategory": [
                {"category": x.category, "subcategory": x.subcategory, "total": f"{x.total.amount:.2f}"}
                for x in by_sub
            ],
            "monthly_by_kind": [
                {"year": x.month.year, "month": x.month.month, "kind": x.kind.value, "total": f"{x.total.amount:.2f}"}
                for x in by_month_kind
            ],
        }

    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        logger.exception("Failed to compute budget summary: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")