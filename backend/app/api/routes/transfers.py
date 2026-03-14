from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
import datetime as dt

from app.api.deps import get_account_repo, get_tx_repo, get_request_context
from app.api.routes.account_transactions import _tx_to_response
from app.api.schemas.transfers import TransferResponse
from app.domain.transaction import TransactionKind
from app.identity.request_context import RequestContext

router = APIRouter(prefix="/transfers", tags=["transfers"])


class TransferListItem(BaseModel):
    transfer_id: UUID
    date: dt.date
    amount: str
    currency: str
    label: str | None
    from_account_id: str
    from_account_name: str
    to_account_id: str
    to_account_name: str
    from_transaction_id: str
    to_transaction_id: str


class LinkTransferRequest(BaseModel):
    from_transaction_id: UUID
    to_transaction_id: UUID


@router.post("/link", response_model=TransferResponse, status_code=201)
def link_transactions_as_transfer(
    payload: LinkTransferRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> TransferResponse:
    tx_repo = get_tx_repo()
    try:
        tx_from, tx_to = tx_repo.link_as_transfer(
            tx_from_id=payload.from_transaction_id,
            tx_to_id=payload.to_transaction_id,
            profile_id=ctx.profile_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Identifier quelle jambe est "from" (montant négatif)
    if tx_from.amount.amount > 0:
        tx_from, tx_to = tx_to, tx_from

    return TransferResponse(
        transfer_id=tx_from.transfer_id,  # type: ignore[arg-type]
        from_transaction=_tx_to_response(tx_from),
        to_transaction=_tx_to_response(tx_to),
    )


@router.get("", response_model=list[TransferListItem])
def list_transfers(ctx: RequestContext = Depends(get_request_context)) -> list[TransferListItem]:
    tx_repo = get_tx_repo()
    account_repo = get_account_repo()

    # Toutes les transactions TRANSFER du profil
    all_txs = tx_repo.list(profile_id=ctx.profile_id)
    transfer_txs = [t for t in all_txs if t.kind == TransactionKind.TRANSFER and t.transfer_id is not None]

    if not transfer_txs:
        return []

    # Charger les comptes une seule fois
    accounts = {a.id: a for a in account_repo.list_accounts(profile_id=ctx.profile_id)}

    # Grouper par transfer_id
    by_tid: dict[UUID, list] = {}
    for tx in transfer_txs:
        tid = tx.transfer_id
        by_tid.setdefault(tid, []).append(tx)

    result: list[TransferListItem] = []
    for tid, legs in by_tid.items():
        if len(legs) != 2:
            continue  # Incohérence — on ignore

        # La jambe "from" a un montant négatif
        legs_sorted = sorted(legs, key=lambda t: t.amount.amount)
        tx_from, tx_to = legs_sorted[0], legs_sorted[1]

        from_acc = accounts.get(tx_from.account_id)
        to_acc = accounts.get(tx_to.account_id)
        if from_acc is None or to_acc is None:
            continue

        result.append(TransferListItem(
            transfer_id=tid,
            date=tx_from.date,
            amount=str(abs(tx_from.amount.amount)),
            currency=tx_from.amount.currency.value,
            label=tx_from.label,
            from_account_id=tx_from.account_id,
            from_account_name=from_acc.name,
            to_account_id=tx_to.account_id,
            to_account_name=to_acc.name,
            from_transaction_id=str(tx_from.id),
            to_transaction_id=str(tx_to.id),
        ))

    result.sort(key=lambda t: t.date, reverse=True)
    return result
