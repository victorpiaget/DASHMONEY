from __future__ import annotations

import logging

import datetime as dt

from fastapi import APIRouter, HTTPException, Response, Query

from app.api.deps import get_account_repo, get_tx_repo
from app.api.schemas.accounts import AccountCreateRequest, AccountResponse, AccountTimeSeriesResponse, TimeSeriesPoint,AccountUpdateRequest
from app.domain.account import Account
from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.api.schemas.accounts import AccountBalanceResponse
from app.engine.account_balance import compute_balance
from app.engine.account_timeseries import pick_granularity, compute_timeseries

from uuid import uuid4
from app.api.schemas.transfers import TransferCreateRequest, TransferResponse
from app.domain.transaction import Transaction, TransactionKind

from app.api.routes.account_transactions import _tx_to_response

from app.domain.account import AccountType

from uuid import UUID
from decimal import Decimal
from app.api.schemas.transfers import TransferUpdateRequest


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/{account_id}/transfers", response_model=TransferResponse, status_code=201)
def create_transfer(account_id: str, payload: TransferCreateRequest) -> TransferResponse:

    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    # 1️⃣ Vérifier comptes
    try:
        from_acc = account_repo.get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    try:
        to_acc = account_repo.get_account(payload.to_account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="To account not found")

    if from_acc.id == to_acc.id:
        raise HTTPException(status_code=422, detail="Cannot transfer to same account")

    # 2️⃣ Vérifier devise (MVP)
    if from_acc.currency != to_acc.currency:
        raise HTTPException(status_code=422, detail="Currency mismatch between accounts")

    # 3️⃣ Convertir amount
    try:
        pos_amount = SignedMoney.from_str(payload.amount, from_acc.currency)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    if pos_amount.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be > 0")

    neg_amount = SignedMoney(amount=-pos_amount.amount, currency=pos_amount.currency)

    transfer_id = uuid4()

    # 4️⃣ Séquences
    seq_from = tx_repo.next_sequence(from_acc.id, payload.date)
    seq_to = tx_repo.next_sequence(to_acc.id, payload.date)

    # 5️⃣ Créer transactions
    try:
        tx_from = Transaction.create(
            account_id=from_acc.id,
            date=payload.date,
            sequence=seq_from,
            amount=neg_amount,
            kind=TransactionKind.TRANSFER,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
            transfer_id=transfer_id,
        )

        tx_to = Transaction.create(
            account_id=to_acc.id,
            date=payload.date,
            sequence=seq_to,
            amount=pos_amount,
            kind=TransactionKind.TRANSFER,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
            transfer_id=transfer_id,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 6️⃣ Persister
    tx_repo.add(tx_from)
    tx_repo.add(tx_to)

    return TransferResponse(
        transfer_id=transfer_id,
        from_transaction=_tx_to_response(tx_from),
        to_transaction=_tx_to_response(tx_to),
    )


@router.delete("/{account_id}/transfers/{transfer_id}", status_code=204)
def delete_transfer(account_id: str, transfer_id: UUID) -> None:
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    # 1) verify from account exists
    try:
        from_acc = account_repo.get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    # 2) delete atomically in repo
    try:
        # optional: check belongs to from account
        # we can do a quick read by listing and finding the negative leg
        # but simplest: delete then verify is not possible; so we verify first:
        legs = [t for t in tx_repo.list(account_id=from_acc.id) if t.transfer_id == transfer_id]
        if not legs:
            raise HTTPException(status_code=404, detail="Transfer not found for this from account")

        tx_repo.delete_transfer(transfer_id=transfer_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transfer not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{account_id}/transfers/{transfer_id}", response_model=TransferResponse)
def update_transfer(account_id: str, transfer_id: UUID, payload: TransferUpdateRequest) -> TransferResponse:
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    # 1️⃣ Vérifier compte "from" existe (comme POST)
    try:
        from_acc = account_repo.get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    # 2️⃣ Charger les 2 legs via transfer_id (en lisant les tx du repo)
    # On utilise le repo directement via update_transfer, mais on doit valider la currency avec une amount si fournie.
    new_amount_pos = None
    if payload.amount is not None:
        try:
            new_amount_pos = SignedMoney.from_str(payload.amount, from_acc.currency)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))
        if new_amount_pos.amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be > 0")

    # 3️⃣ Appliquer update atomique (2 legs)
    try:
        tx_from, tx_to = tx_repo.update_transfer(
            transfer_id=transfer_id,
            new_date=payload.date,
            new_amount_pos=new_amount_pos,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Transfer not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4️⃣ Vérifier que le transfert appartient bien au compte from (cohérence d’API)
    if tx_from.account_id != from_acc.id:
        # tu as appelé /accounts/{account_id}/transfers/{transfer_id} avec un mauvais account_id
        raise HTTPException(status_code=422, detail="transfer_id does not belong to this from account")

    return TransferResponse(
        transfer_id=transfer_id,
        from_transaction=_tx_to_response(tx_from),
        to_transaction=_tx_to_response(tx_to),
    )

@router.post("", status_code=201, response_model=AccountResponse)
def create_account(req: AccountCreateRequest) -> AccountResponse:
    repo = get_account_repo()

    # currency
    try:
        currency = Currency(req.currency.strip())
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid currency")

    # opening balance
    try:
        opening_balance = SignedMoney.from_str(req.opening_balance.strip(), currency)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid opening_balance format")
    
    # account type
    try:
        account_type = AccountType(req.account_type.strip())
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid account_type")

    # domain object
    try:
        account = Account(
            id=req.id.strip(),
            name=req.name.strip(),
            currency=currency,
            opening_balance=opening_balance,
            opened_on=req.opened_on,
            account_type=account_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # uniqueness
    try:
        repo.get_account(account.id)
        raise HTTPException(status_code=409, detail="Account id already exists")
    except KeyError:
        pass

    # persist
    try:
        repo.add(account)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _account_to_response(account)


@router.get("", response_model=list[AccountResponse])
def list_accounts() -> list[AccountResponse]:
    try:
        repo = get_account_repo()
        accounts = repo.list_accounts()
        return [_account_to_response(a) for a in accounts]
    except Exception as e:
        logger.exception("Failed to list accounts: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")

@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, cascade: bool = Query(default=True)) -> Response:
    # 1) vérifier que le compte existe
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    tx_repo = get_tx_repo()

    # 2) cascade transactions
    if cascade:
        txs = tx_repo.list(account_id=acc.id)
        for t in txs:
            tx_repo.delete(account_id=acc.id, tx_id=t.id)

    # 3) supprimer le compte
    deleted = get_account_repo().delete(account_id=acc.id)
    if not deleted:
        # (rare) si supprimé entre-temps
        raise HTTPException(status_code=404, detail="Account not found")

    return Response(status_code=204)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(account_id: str, req: AccountUpdateRequest) -> AccountResponse:
    repo = get_account_repo()

    # exists?
    try:
        repo.get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    # parse account_type if provided
    account_type = None
    if req.account_type is not None:
        try:
            account_type = AccountType(req.account_type.strip())
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid account_type")

    try:
        updated = repo.update(
            account_id=account_id,
            name=req.name,
            account_type=account_type,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _account_to_response(updated)



@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
def get_account_balance(
    account_id: str,
    at: dt.date | None = Query(default=None),
) -> AccountBalanceResponse:
    # 1) compte
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    # 2) tx
    txs = get_tx_repo().list(account_id=acc.id)

    # 3) compute
    opening, tx_sum, balance, n = compute_balance(
        opening_balance=acc.opening_balance,
        transactions=txs,
        at=at,
    )

    return AccountBalanceResponse(
        account_id=acc.id,
        currency=acc.currency.value,
        at=at,
        opening_balance=str(opening.amount),
        transactions_sum=str(tx_sum.amount),
        balance=str(balance.amount),
        transactions_count=n,
    )

@router.get("/{account_id}/timeseries", response_model=AccountTimeSeriesResponse)
def account_timeseries(
    account_id: str,
    date_from: dt.date = Query(..., alias="from"),
    date_to: dt.date = Query(..., alias="to"),
    granularity: str = Query(default="auto", pattern="^(auto|daily|weekly|monthly|yearly)$"),
) -> AccountTimeSeriesResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    txs = get_tx_repo().list(account_id=acc.id)

    g = pick_granularity(date_from, date_to) if granularity == "auto" else granularity

    raw = compute_timeseries(
        opening_balance=acc.opening_balance,
        transactions=txs,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
    )

    points = [
        TimeSeriesPoint(
            bucket=p["bucket"],
            income=str(p["income"]),
            expense=str(p["expense"]),
            net=str(p["net"]),
            balance_start=str(p["balance_start"]), 
            balance_end=str(p["balance_end"]),
        )
        for p in raw
    ]

    return AccountTimeSeriesResponse(
        account_id=acc.id,
        currency=acc.currency.value,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
        points=points,
    )



def _account_to_response(acc: Account) -> AccountResponse:
    return AccountResponse(
        id=acc.id,
        name=acc.name,
        currency=str(acc.currency),
        opening_balance=str(acc.opening_balance),
        opened_on=acc.opened_on,
        account_type=acc.account_type.value,
    )



