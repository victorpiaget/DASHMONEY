from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from uuid import UUID

from app.api.deps import get_account_repo, get_tx_repo, get_request_context
from app.api.schemas.transactions import TransactionResponse
from app.domain.transaction import TransactionKind
from app.identity.request_context import RequestContext
from app.services.transaction_query_service import TransactionQuery, apply_transaction_query, SortBy, SortDir

router = APIRouter(prefix="/transactions", tags=["transactions-global"])


class GlobalTransactionResponse(TransactionResponse):
    account_name: str
    account_currency: str


@router.get("", response_model=list[GlobalTransactionResponse])
def list_transactions(
    account_ids: str | None = Query(default=None, description="CSV of account IDs"),
    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),
    kinds: list[TransactionKind] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    q: str | None = Query(default=None, description="Search label"),
    sort_by: SortBy = Query(default="date"),
    sort_dir: SortDir = Query(default="desc"),
    limit: int = Query(default=500, le=2000),
    ctx: RequestContext = Depends(get_request_context),
) -> list[GlobalTransactionResponse]:
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    all_accounts = acc_repo.list_accounts(profile_id=ctx.profile_id)
    account_map = {a.id: a for a in all_accounts}

    # Filtre optionnel par account_ids
    if account_ids and account_ids.strip():
        selected_ids = {x.strip() for x in account_ids.split(",") if x.strip()}
        target_accounts = [a for a in all_accounts if a.id in selected_ids]
    else:
        target_accounts = all_accounts

    # Récupère toutes les transactions des comptes ciblés
    all_txs = []
    for acc in target_accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id, profile_id=ctx.profile_id))

    # Applique les filtres + tri
    query = TransactionQuery(
        date_from=date_from,
        date_to=date_to,
        kinds=set(kinds) if kinds else None,
        categories=set(categories) if categories else None,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    filtered = apply_transaction_query(all_txs, query)[:limit]

    result = []
    for tx in filtered:
        acc = account_map.get(tx.account_id)
        result.append(GlobalTransactionResponse(
            id=str(tx.id),
            account_id=tx.account_id,
            account_name=acc.name if acc else tx.account_id,
            account_currency=acc.currency.value if acc else "EUR",
            date=tx.date,
            sequence=tx.sequence,
            amount=str(tx.amount.amount),
            currency=tx.amount.currency,
            kind=tx.kind,
            category=tx.category,
            subcategory=tx.subcategory,
            label=tx.label,
            created_at=tx.created_at,
            transfer_id=tx.transfer_id,
        ))

    return result
