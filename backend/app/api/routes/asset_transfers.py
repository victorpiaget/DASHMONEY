from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import (
    get_portfolio_repo, get_instrument_repo, get_trade_repo,
    get_request_context, get_write_context,
    get_portfolio_snapshot_repo, get_price_repo,
)
from app.api.schemas.trades import TradeOut
from app.domain.trade import Trade, TradeSide, TradeType
from app.identity.request_context import RequestContext
from app.services.snapshot_recompute_service import recompute_snapshots_from


def _schedule_recompute(
    background: BackgroundTasks,
    *,
    portfolio_id,
    from_date: dt.date,
    profile_id: str,
) -> None:
    background.add_task(
        recompute_snapshots_from,
        portfolio_id=portfolio_id,
        from_date=from_date,
        portfolio_repo=get_portfolio_repo(),
        trade_repo=get_trade_repo(),
        price_repo=get_price_repo(),
        snapshot_repo=get_portfolio_snapshot_repo(),
        instrument_repo=get_instrument_repo(),
        profile_id=profile_id,
    )

router = APIRouter(prefix="/asset-transfers", tags=["asset-transfers"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class AssetTransferPayload(BaseModel):
    from_portfolio_id: UUID
    to_portfolio_id: UUID
    instrument_symbol: str
    quantity: str
    fees: str | None = None
    date: dt.date


class AssetTransferRecord(BaseModel):
    sell_trade_id: str
    buy_trade_id: str | None
    date: dt.date
    instrument_symbol: str
    quantity: str
    fees: str
    from_portfolio_id: str
    from_portfolio_name: str
    to_portfolio_id: str | None
    to_portfolio_name: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _trade_to_out(t: Trade) -> TradeOut:
    return TradeOut(
        id=t.id, portfolio_id=t.portfolio_id, date=t.date, side=t.side.value,
        trade_type=t.trade_type.value,
        instrument_symbol=t.instrument_symbol, quantity=str(t.quantity), price=str(t.price),
        fees=str(t.fees), currency=t.currency.value, label=t.label,
        linked_cash_tx_id=t.linked_cash_tx_id,
    )


# ── POST /asset-transfers ──────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_asset_transfer(
    payload: AssetTransferPayload,
    background: BackgroundTasks,
    ctx: RequestContext = Depends(get_write_context),
) -> dict:
    p_repo = get_portfolio_repo()
    i_repo = get_instrument_repo()
    t_repo = get_trade_repo()

    try:
        from_p = p_repo.get(payload.from_portfolio_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="source portfolio not found")

    try:
        to_p = p_repo.get(payload.to_portfolio_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="destination portfolio not found")

    if from_p.id == to_p.id:
        raise HTTPException(status_code=422, detail="source and destination portfolios must be different")

    try:
        inst = i_repo.get(payload.instrument_symbol)
    except KeyError:
        raise HTTPException(status_code=404, detail="instrument not found")

    try:
        qty = Decimal(payload.quantity)
        fees = Decimal(payload.fees or "0")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid numeric field: {e}")

    if qty <= 0:
        raise HTTPException(status_code=422, detail="quantity must be positive")

    label_sell = f"Transfert vers {to_p.name}"
    label_buy = f"Transfert depuis {from_p.name}"

    # Prix = 1 (requis par le domaine Trade). Pas de transaction cash miroir —
    # un transfert d'actif ne génère pas de flux monétaire.
    # SELL dans la source — pas de vérification de position (transfert historique possible).
    try:
        sell_trade = Trade.create(
            portfolio_id=from_p.id, date=payload.date, side=TradeSide.SELL,
            instrument_symbol=inst.symbol, quantity=qty, price=Decimal("1"), fees=fees,
            currency=from_p.currency, label=label_sell, linked_cash_tx_id=None,
            trade_type=TradeType.TRANSFER,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    t_repo.add(sell_trade, profile_id=ctx.profile_id)

    # BUY dans la destination
    try:
        buy_trade = Trade.create(
            portfolio_id=to_p.id, date=payload.date, side=TradeSide.BUY,
            instrument_symbol=inst.symbol, quantity=qty, price=Decimal("1"), fees=Decimal("0"),
            currency=to_p.currency, label=label_buy, linked_cash_tx_id=None,
            trade_type=TradeType.TRANSFER,
        )
    except Exception as e:
        try:
            t_repo.delete(trade_id=sell_trade.id, profile_id=ctx.profile_id)
        except Exception:
            pass
        raise HTTPException(status_code=422, detail=str(e))

    t_repo.add(buy_trade, profile_id=ctx.profile_id)

    # Un transfert impacte les deux portefeuilles — on recompute chacun depuis la date du transfert
    _schedule_recompute(background, portfolio_id=from_p.id, from_date=payload.date, profile_id=ctx.profile_id)
    _schedule_recompute(background, portfolio_id=to_p.id, from_date=payload.date, profile_id=ctx.profile_id)

    return {
        "sell": _trade_to_out(sell_trade),
        "buy": _trade_to_out(buy_trade),
    }


# ── GET /asset-transfers ───────────────────────────────────────────────────────

@router.get("", response_model=list[AssetTransferRecord])
def list_asset_transfers(
    ctx: RequestContext = Depends(get_request_context),
) -> list[AssetTransferRecord]:
    p_repo = get_portfolio_repo()
    t_repo = get_trade_repo()

    portfolios = {str(p.id): p for p in p_repo.list(profile_id=ctx.profile_id)}

    # Toutes les trades du profil sans transaction cash miroir
    all_trades = t_repo.list(profile_id=ctx.profile_id)

    # SELL de transfert = SELL sans cash mirror dont le label commence par "Transfert vers "
    sell_transfers = [
        t for t in all_trades
        if t.side == TradeSide.SELL
        and t.linked_cash_tx_id is None
        and (t.label or "").startswith("Transfert vers ")
    ]

    # BUY de transfert indexés par (portfolio_id, symbol, date, quantity)
    # pour retrouver la contrepartie
    buy_index: dict[tuple, Trade] = {}
    for t in all_trades:
        if t.side == TradeSide.BUY and t.linked_cash_tx_id is None and (t.label or "").startswith("Transfert depuis "):
            key = (str(t.portfolio_id), t.instrument_symbol.upper(), t.date, t.quantity)
            buy_index[key] = t

    records: list[AssetTransferRecord] = []
    for sell in sell_transfers:
        from_p = portfolios.get(str(sell.portfolio_id))
        if from_p is None:
            continue

        dest_name = (sell.label or "").removeprefix("Transfert vers ").strip()

        # Chercher le BUY correspondant dans n'importe quel portfolio
        buy: Trade | None = None
        dest_portfolio_id: str | None = None
        for pid, p in portfolios.items():
            if p.name == dest_name:
                key = (pid, sell.instrument_symbol.upper(), sell.date, sell.quantity)
                buy = buy_index.get(key)
                if buy is not None:
                    dest_portfolio_id = pid
                    break

        records.append(AssetTransferRecord(
            sell_trade_id=str(sell.id),
            buy_trade_id=str(buy.id) if buy else None,
            date=sell.date,
            instrument_symbol=sell.instrument_symbol,
            quantity=str(sell.quantity),
            fees=str(sell.fees),
            from_portfolio_id=str(sell.portfolio_id),
            from_portfolio_name=from_p.name,
            to_portfolio_id=dest_portfolio_id,
            to_portfolio_name=dest_name,
        ))

    records.sort(key=lambda r: r.date, reverse=True)
    return records


# ── DELETE /asset-transfers/{sell_trade_id} ────────────────────────────────────

@router.delete("/{sell_trade_id}", status_code=204)
def delete_asset_transfer(
    sell_trade_id: UUID,
    background: BackgroundTasks,
    ctx: RequestContext = Depends(get_write_context),
) -> None:
    t_repo = get_trade_repo()

    try:
        sell = t_repo.get(sell_trade_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="trade not found")

    if sell.side != TradeSide.SELL or not (sell.label or "").startswith("Transfert vers "):
        raise HTTPException(status_code=422, detail="not an asset transfer trade")

    # Trouver et supprimer le BUY correspondant
    all_trades = t_repo.list(profile_id=ctx.profile_id)
    # Le SELL est labelle "Transfert vers {dest_name}" et le BUY est labelle
    # "Transfert depuis {from_portfolio_name}". Pour retrouver le BUY on a besoin
    # du nom du portfolio source (celui qui contient le SELL).
    p_repo = get_portfolio_repo()
    try:
        from_portfolio = p_repo.get(sell.portfolio_id, profile_id=ctx.profile_id)
        from_portfolio_name = from_portfolio.name
    except KeyError:
        from_portfolio_name = None

    buy_portfolio_id = None
    for t in all_trades:
        if (
            t.side == TradeSide.BUY
            and t.linked_cash_tx_id is None
            and from_portfolio_name is not None
            and (t.label or "") == f"Transfert depuis {from_portfolio_name}"
            and t.instrument_symbol.upper() == sell.instrument_symbol.upper()
            and t.date == sell.date
            and t.quantity == sell.quantity
        ):
            buy_portfolio_id = t.portfolio_id
            t_repo.delete(trade_id=t.id, profile_id=ctx.profile_id)
            break

    t_repo.delete(trade_id=sell_trade_id, profile_id=ctx.profile_id)

    # Recompute des deux portefeuilles concernés
    _schedule_recompute(background, portfolio_id=sell.portfolio_id, from_date=sell.date, profile_id=ctx.profile_id)
    if buy_portfolio_id is not None:
        _schedule_recompute(background, portfolio_id=buy_portfolio_id, from_date=sell.date, profile_id=ctx.profile_id)
