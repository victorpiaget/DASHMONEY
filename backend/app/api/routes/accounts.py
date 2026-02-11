from __future__ import annotations

import logging
import datetime as dt
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_account_repo, get_tx_repo
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.engine.running_balance import compute_running_balance_strict
from app.api.schemas.transactions import TransactionResponse
from app.domain.transaction import Transaction
from app.api.schemas.transactions import AccountTransactionCreateRequest
from app.api.schemas.transactions import TransactionResponse
from app.services.transaction_query_service import TransactionQuery, apply_transaction_query

from app.services.transaction_query_service import (  # <-- nouveau
    TransactionQuery,
    apply_transaction_query,
)

from app.engine.budget import (
    totals_by_kind,
    expense_totals_by_category,
    expense_totals_by_subcategory,
    monthly_totals_by_kind,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts():
    try:
        repo = get_account_repo()
        accounts = repo.list_accounts()
        return [
            {
                "id": a.id,
                "name": a.name,
                "currency": a.currency.value,
                "opening_balance": f"{a.opening_balance.amount:.2f}",
                "opened_on": a.opened_on.isoformat(),
            }
            for a in accounts
        ]
    except Exception as e:
        logger.exception("Failed to list accounts: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")

@router.get("/{account_id}/transactions", response_model=list[TransactionResponse])
def list_account_transactions(
    account_id: str,

    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),

    kinds: list[TransactionKind] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    subcategories: list[str] | None = Query(default=None),

    q: str | None = Query(default=None),

    sort_by: str = Query(default="date", pattern="^(date|amount|kind|category|subcategory|label)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[TransactionResponse]:
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    txs = get_tx_repo().list(account_id=acc.id)

    query_obj = TransactionQuery(
        date_from=date_from,
        date_to=date_to,
        kinds=set(kinds) if kinds else None,
        categories=set(c.strip() for c in categories if c and c.strip()) if categories else None,
        subcategories=set(s.strip() for s in subcategories if s and s.strip()) if subcategories else None,
        q=q,
        sort_by=sort_by,   # type: ignore[arg-type]
        sort_dir=sort_dir, # type: ignore[arg-type]
    )

    txs = apply_transaction_query(txs, query_obj)
    return [_to_response(t) for t in txs]   

@router.post("/{account_id}/transactions", response_model=TransactionResponse, status_code=201)
def create_account_transaction(
    account_id: str,
    payload: AccountTransactionCreateRequest,
) -> TransactionResponse:
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    # 1) SignedMoney: currency = currency du compte
    try:
        amount = SignedMoney.from_str(payload.amount, acc.currency)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 2) sequence auto
    tx_repo = get_tx_repo()
    seq = tx_repo.next_sequence(acc.id, payload.date)

    # 3) Transaction.create (domain rules)
    try:
        tx = Transaction.create(
            account_id=acc.id,
            date=payload.date,
            sequence=seq,
            amount=amount,
            kind=payload.kind,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4) add
    try:
        tx_repo.add(tx)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _to_response(tx)

@router.get("/{account_id}/budget-summary")
def budget_summary(
    account_id: str,
    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),
):
    try:
        acc = get_account_repo().get_account(account_id)
        txs = get_tx_repo().list(account_id=acc.id)

        # filtre période uniquement (MVP)
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
            "totals_by_kind": [
                {"kind": x.kind.value, "total": f"{x.total.amount:.2f}"}
                for x in kb
            ],
            "expense_by_category": [
                {"category": x.category, "total": f"{x.total.amount:.2f}"}
                for x in by_cat
            ],
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


def _to_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(tx.id),
        account_id=tx.account_id,
        date=tx.date,
        sequence=tx.sequence,
        amount=str(tx.amount.amount),     # Decimal -> string
        currency=tx.amount.currency,
        kind=tx.kind,
        category=tx.category,
        subcategory=tx.subcategory,
        label=tx.label,
        created_at=tx.created_at,
    )

