from __future__ import annotations

import datetime as dt
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID

from app.api.deps import get_portfolio_repo, get_instrument_repo, get_trade_repo, get_account_repo, get_tx_repo
from app.api.schemas.trades import TradeCreate, TradeOut, PositionOut, TradePatch
from app.domain.trade import Trade, TradeSide
from app.domain.transaction import Transaction, TransactionKind
from app.domain.signed_money import SignedMoney
from app.engine.portfolio_positions import compute_positions


router = APIRouter(prefix="/portfolios/{portfolio_id}/trades", tags=["trades"])


def _trade_to_out(t: Trade) -> TradeOut:
    return TradeOut(
        id=t.id,
        portfolio_id=t.portfolio_id,
        date=t.date,
        side=t.side.value,
        instrument_symbol=t.instrument_symbol,
        quantity=str(t.quantity),
        price=str(t.price),
        fees=str(t.fees),
        currency=t.currency.value,
        label=t.label,
        linked_cash_tx_id=t.linked_cash_tx_id,
    )


def _create_cash_mirror_tx(
    *,
    cash_account_id: str,
    date: dt.date,
    cash_amount: SignedMoney,
    label: str | None,
) -> Transaction:
    """
    Crée la transaction miroir dans le compte passerelle en utilisant ton flux standard
    (next_sequence + Transaction.create + repo.add).
    """
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    try:
        acc = acc_repo.get_account(cash_account_id)
    except KeyError:
        raise HTTPException(status_code=500, detail="cash pass-through account missing (should not happen)")

    seq = tx_repo.next_sequence(acc.id, date)

    # kind selon signe
    kind = TransactionKind.INCOME if cash_amount.amount > 0 else TransactionKind.EXPENSE

    try:
        tx = Transaction.create(
            account_id=acc.id,
            date=date,
            sequence=seq,
            amount=cash_amount,
            kind=kind,
            category="INVEST",
            subcategory=None,
            label=label,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    tx_repo.add(tx)
    return tx


@router.post("", response_model=TradeOut, status_code=201)
def create_trade(portfolio_id: UUID, payload: TradeCreate) -> TradeOut:
    p_repo = get_portfolio_repo()
    i_repo = get_instrument_repo()
    t_repo = get_trade_repo()

    # portfolio
    try:
        p = p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    # instrument exists
    try:
        inst = i_repo.get(payload.instrument_symbol)
    except KeyError:
        raise HTTPException(status_code=404, detail="instrument not found")

    # currency check: pricing currency must match portfolio currency (MVP)
    if inst.currency != p.currency:
        raise HTTPException(status_code=422, detail="instrument currency must match portfolio currency (MVP)")

    # parse decimals
    try:
        side = TradeSide(payload.side.strip())
        qty = Decimal(payload.quantity)
        price = Decimal(payload.price)
        fees = Decimal(payload.fees or "0")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid numeric field: {e}")

    # cash amount (SignedMoney)
    gross = qty * price
    if side == TradeSide.BUY:
        net = -(gross + fees)
    else:
        net = (gross - fees)

    cash_amount = SignedMoney(amount=net, currency=p.currency)

    # create cash mirror tx first
    tx = _create_cash_mirror_tx(
        cash_account_id=p.cash_account_id,
        date=payload.date,
        cash_amount=cash_amount,
        label=payload.label or f"{side.value} {inst.symbol}",
    )

    # create trade with linked tx id
    try:
        trade = Trade.create(
            portfolio_id=p.id,
            date=payload.date,
            side=side,
            instrument_symbol=inst.symbol,
            quantity=qty,
            price=price,
            fees=fees,
            currency=p.currency,
            label=payload.label,
            linked_cash_tx_id=tx.id,
        )
    except Exception as e:
        # best effort rollback: delete created tx
        try:
            get_tx_repo().delete(account_id=p.cash_account_id, tx_id=tx.id)
        except Exception:
            pass
        raise HTTPException(status_code=422, detail=str(e))

    t_repo.add(trade)
    return _trade_to_out(trade)


@router.get("", response_model=list[TradeOut])
def list_trades(portfolio_id: UUID):
    p_repo = get_portfolio_repo()
    t_repo = get_trade_repo()

    try:
        p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    return [_trade_to_out(t) for t in t_repo.list(portfolio_id=portfolio_id)]


@router.patch("/{trade_id}", response_model=TradeOut)
def patch_trade(portfolio_id: UUID, trade_id: UUID, payload: TradePatch) -> TradeOut:
    p_repo = get_portfolio_repo()
    t_repo = get_trade_repo()

    try:
        p = p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    try:
        base = t_repo.get(trade_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="trade not found")

    if base.portfolio_id != p.id:
        raise HTTPException(status_code=422, detail="trade does not belong to this portfolio")

    patch: dict = {}

    if payload.date is not None:
        patch["date"] = payload.date
    if payload.side is not None:
        patch["side"] = TradeSide(payload.side.strip())
    if payload.quantity is not None:
        patch["quantity"] = Decimal(payload.quantity)
    if payload.price is not None:
        patch["price"] = Decimal(payload.price)
    if payload.fees is not None:
        patch["fees"] = Decimal(payload.fees)
    if payload.label is not None:
        patch["label"] = payload.label

    # If anything affecting cash changes, update the linked cash tx too (MVP simple: create new tx + delete old)
    side = patch.get("side", base.side)
    qty = patch.get("quantity", base.quantity)
    price = patch.get("price", base.price)
    fees = patch.get("fees", base.fees)
    date = patch.get("date", base.date)

    gross = qty * price
    net = -(gross + fees) if side == TradeSide.BUY else (gross - fees)
    cash_amount = SignedMoney(amount=net, currency=p.currency)

    # create new cash tx
    new_tx = _create_cash_mirror_tx(
        cash_account_id=p.cash_account_id,
        date=date,
        cash_amount=cash_amount,
        label=patch.get("label", base.label) or f"{side.value} {base.instrument_symbol}",
    )

    # delete old cash tx (best effort)
    if base.linked_cash_tx_id is not None:
        try:
            get_tx_repo().delete(account_id=p.cash_account_id, tx_id=base.linked_cash_tx_id)
        except Exception:
            pass

    patch["linked_cash_tx_id"] = new_tx.id
    patch["currency"] = p.currency

    updated = t_repo.update(trade_id=trade_id, patch=patch)
    return _trade_to_out(updated)


@router.delete("/{trade_id}", status_code=204)
def delete_trade(portfolio_id: UUID, trade_id: UUID) -> None:
    p_repo = get_portfolio_repo()
    t_repo = get_trade_repo()

    try:
        p = p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    try:
        trade = t_repo.get(trade_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="trade not found")

    if trade.portfolio_id != p.id:
        raise HTTPException(status_code=422, detail="trade does not belong to this portfolio")

    # delete trade (tombstone)
    ok = t_repo.delete(trade_id=trade_id)
    if not ok:
        raise HTTPException(status_code=404, detail="trade not found")

    # delete linked cash tx
    if trade.linked_cash_tx_id is not None:
        try:
            get_tx_repo().delete(account_id=p.cash_account_id, tx_id=trade.linked_cash_tx_id)
        except Exception:
            pass


# Positions endpoint (same file, different router for simplicity)
pos_router = APIRouter(prefix="/portfolios/{portfolio_id}", tags=["positions"])


@pos_router.get("/positions", response_model=list[PositionOut])
def get_positions(
    portfolio_id: UUID,
    as_of: dt.date | None = Query(default=None),
):
    p_repo = get_portfolio_repo()
    t_repo = get_trade_repo()

    try:
        p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    trades = t_repo.list(portfolio_id=portfolio_id)
    pos = compute_positions(trades=trades, portfolio_id=portfolio_id, as_of=as_of)

    return [PositionOut(instrument_symbol=sym, quantity=str(qty)) for sym, qty in sorted(pos.items())]