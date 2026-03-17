from __future__ import annotations

import logging

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response, Query

from app.api.deps import get_account_repo, get_tx_repo, get_request_context, get_write_context
from app.api.schemas.accounts import AccountCreateRequest, AccountResponse, AccountTimeSeriesResponse, TimeSeriesPoint, AccountUpdateRequest
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
from app.identity.request_context import RequestContext

from uuid import UUID
from decimal import Decimal
from app.api.schemas.transfers import TransferUpdateRequest


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/{account_id}/transfers", response_model=TransferResponse, status_code=201)
def create_transfer(
    account_id: str,
    payload: TransferCreateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> TransferResponse:

    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    try:
        from_acc = account_repo.get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    try:
        to_acc = account_repo.get_account(payload.to_account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="To account not found")

    if from_acc.id == to_acc.id:
        raise HTTPException(status_code=422, detail="Cannot transfer to same account")

    if from_acc.currency != to_acc.currency:
        raise HTTPException(status_code=422, detail="Currency mismatch between accounts")

    try:
        pos_amount = SignedMoney.from_str(payload.amount, from_acc.currency)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    if pos_amount.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be > 0")

    neg_amount = SignedMoney(amount=-pos_amount.amount, currency=pos_amount.currency)

    transfer_id = uuid4()

    seq_from = tx_repo.next_sequence(from_acc.id, payload.date, profile_id=ctx.profile_id)
    seq_to = tx_repo.next_sequence(to_acc.id, payload.date, profile_id=ctx.profile_id)

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

    tx_repo.add(tx_from, profile_id=ctx.profile_id)
    tx_repo.add(tx_to, profile_id=ctx.profile_id)

    return TransferResponse(
        transfer_id=transfer_id,
        from_transaction=_tx_to_response(tx_from),
        to_transaction=_tx_to_response(tx_to),
    )


@router.delete("/{account_id}/transfers/{transfer_id}", status_code=204)
def delete_transfer(
    account_id: str,
    transfer_id: UUID,
    ctx: RequestContext = Depends(get_write_context),
) -> None:
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    try:
        from_acc = account_repo.get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    try:
        legs = [t for t in tx_repo.list(account_id=from_acc.id, profile_id=ctx.profile_id) if t.transfer_id == transfer_id]
        if not legs:
            raise HTTPException(status_code=404, detail="Transfer not found for this from account")

        tx_repo.delete_transfer(transfer_id=transfer_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transfer not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{account_id}/transfers/{transfer_id}", response_model=TransferResponse)
def update_transfer(
    account_id: str,
    transfer_id: UUID,
    payload: TransferUpdateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> TransferResponse:
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()

    try:
        from_acc = account_repo.get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="From account not found")

    new_amount_pos = None
    if payload.amount is not None:
        try:
            new_amount_pos = SignedMoney.from_str(payload.amount, from_acc.currency)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))
        if new_amount_pos.amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be > 0")

    try:
        tx_from, tx_to = tx_repo.update_transfer(
            transfer_id=transfer_id,
            new_date=payload.date,
            new_amount_pos=new_amount_pos,
            category=payload.category,
            subcategory=payload.subcategory,
            label=payload.label,
            profile_id=ctx.profile_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Transfer not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if tx_from.account_id != from_acc.id:
        raise HTTPException(status_code=422, detail="transfer_id does not belong to this from account")

    return TransferResponse(
        transfer_id=transfer_id,
        from_transaction=_tx_to_response(tx_from),
        to_transaction=_tx_to_response(tx_to),
    )


@router.post("", status_code=201, response_model=AccountResponse)
def create_account(
    req: AccountCreateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> AccountResponse:
    repo = get_account_repo()
    pid = ctx.profile_id

    try:
        currency = Currency(req.currency.strip())
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid currency")

    try:
        opening_balance = SignedMoney.from_str(req.opening_balance.strip(), currency)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid opening_balance format")

    try:
        account_type = AccountType(req.account_type.strip())
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid account_type")

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

    try:
        repo.add(account, profile_id=pid)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _account_to_response(account, profile_id=pid)


@router.get("", response_model=list[AccountResponse])
def list_accounts(ctx: RequestContext = Depends(get_request_context)) -> list[AccountResponse]:
    try:
        accounts = get_account_repo().list_accounts(profile_id=ctx.profile_id)
        return [_account_to_response(a, profile_id=ctx.profile_id) for a in accounts]
    except Exception as e:
        logger.exception("Failed to list accounts: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


@router.delete("/{account_id}", status_code=204)
def delete_account(
    account_id: str,
    cascade: bool = Query(default=True),
    ctx: RequestContext = Depends(get_write_context),
) -> Response:
    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    tx_repo = get_tx_repo()

    if cascade:
        txs = tx_repo.list(account_id=acc.id, profile_id=ctx.profile_id)
        for t in txs:
            tx_repo.delete(account_id=acc.id, tx_id=t.id, profile_id=ctx.profile_id)

    deleted = get_account_repo().delete(account_id=acc.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")

    return Response(status_code=204)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    req: AccountUpdateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> AccountResponse:
    repo = get_account_repo()

    try:
        repo.get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

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
            profile_id=ctx.profile_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _account_to_response(updated, profile_id=ctx.profile_id)


@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
def get_account_balance(
    account_id: str,
    at: dt.date | None = Query(default=None),
    ctx: RequestContext = Depends(get_request_context),
) -> AccountBalanceResponse:
    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    txs = get_tx_repo().list(account_id=acc.id, profile_id=ctx.profile_id)

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
    ctx: RequestContext = Depends(get_request_context),
) -> AccountTimeSeriesResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    txs = get_tx_repo().list(account_id=acc.id, profile_id=ctx.profile_id)

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


def _account_to_response(a: Account, *, profile_id: str) -> AccountResponse:
    return AccountResponse(
        id=a.id,
        name=a.name,
        currency=a.currency.value,
        opening_balance=str(a.opening_balance.amount),
        opened_on=a.opened_on,
        account_type=a.account_type.value,
        profile_id=profile_id,
    )
