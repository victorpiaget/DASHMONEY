from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.deps import get_account_repo, get_tx_repo
from app.api.schemas.transactions import AccountTransactionCreateRequest, TransactionResponse,TransactionUpdateRequest
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.services.transaction_query_service import TransactionQuery, apply_transaction_query

router = APIRouter(prefix="/accounts", tags=["transactions"])


@router.post("/{account_id}/transactions", response_model=TransactionResponse, status_code=201)
def create_account_transaction(account_id: str, payload: AccountTransactionCreateRequest) -> TransactionResponse:
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        amount = SignedMoney.from_str(payload.amount, acc.currency)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    tx_repo = get_tx_repo()
    seq = tx_repo.next_sequence(acc.id, payload.date)

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

    try:
        tx_repo.add(tx)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _tx_to_response(tx)


@router.delete("/{account_id}/transactions/{tx_id}", status_code=204)
def delete_account_transaction(account_id: str, tx_id: UUID) -> Response:
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    deleted = get_tx_repo().delete(account_id=acc.id, tx_id=tx_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return Response(status_code=204)

@router.patch("/{account_id}/transactions/{tx_id}", response_model=TransactionResponse)
def update_account_transaction(account_id: str, tx_id: UUID, payload: TransactionUpdateRequest) -> TransactionResponse:
    # account exists
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    tx_repo = get_tx_repo()

    # tx exists
    existing = tx_repo.get(tx_id)
    if existing is None or existing.account_id != acc.id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if existing.kind == TransactionKind.TRANSFER or existing.transfer_id is not None:
        raise HTTPException(status_code=422, detail="Transfers must be updated via /transfers endpoint")
    
    amount = None
    if payload.amount is not None:
        # même logique que POST transaction
        amount = SignedMoney.from_str(payload.amount, acc.currency)

    try:
        updated = tx_repo.update(
            account_id=acc.id,
            tx_id=tx_id,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
            date=payload.date,
            amount=amount,
            kind=payload.kind,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Transaction not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _tx_to_response(updated)


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
    return [_tx_to_response(t) for t in txs]


def _tx_to_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(tx.id),
        account_id=tx.account_id,
        date=tx.date,
        sequence=tx.sequence,
        amount=str(tx.amount.amount),
        currency=tx.amount.currency,
        kind=tx.kind,
        category=tx.category,
        subcategory=tx.subcategory,
        label=tx.label,
        created_at=tx.created_at,
    )
