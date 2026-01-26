from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.transactions import TransactionCreateRequest, TransactionResponse
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.repositories.in_memory_transaction_repository import InMemoryTransactionRepository

from app.services.transaction_query_service import (
    TransactionQuery,
    apply_transaction_query,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])

# V0 simple: stockage en mémoire (reset à chaque redémarrage)
_repo = InMemoryTransactionRepository()


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(payload: TransactionCreateRequest) -> TransactionResponse:
    # 1) construire le SignedMoney (domain)
    try:
        amount = SignedMoney.from_str(payload.amount, payload.currency)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 2) sequence auto (solde par ligne)
    seq = _repo.next_sequence(payload.account_id.strip(), payload.date)

    # 3) créer la Transaction (domain rules inside)
    try:
        tx = Transaction.create(
            account_id=payload.account_id,
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

    # 4) stocker
    try:
        _repo.add(tx)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _to_response(tx)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    account_id: str | None = Query(default=None),

    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),

    kinds: list[TransactionKind] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    subcategories: list[str] | None = Query(default=None),

    q: str | None = Query(default=None),

    sort_by: str = Query(default="date", pattern="^(date|amount|kind|category|subcategory|label)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[TransactionResponse]:
    txs = _repo.list(account_id=account_id)

    query = TransactionQuery(
        date_from=date_from,
        date_to=date_to,
        kinds=set(kinds) if kinds else None,
        categories=set([c.strip() for c in categories]) if categories else None,
        subcategories=set([s.strip() for s in subcategories]) if subcategories else None,
        q=q,
        sort_by=sort_by,   # type: ignore[arg-type]
        sort_dir=sort_dir, # type: ignore[arg-type]
    )

    txs = apply_transaction_query(txs, query)
    return [_to_response(t) for t in txs]


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

