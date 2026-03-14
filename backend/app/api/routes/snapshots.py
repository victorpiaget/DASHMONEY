from __future__ import annotations

import datetime as dt

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from fastapi import HTTPException
from app.api.deps import (
    get_portfolio_repo,
    get_trade_repo,
    get_price_repo,
    get_portfolio_snapshot_repo,
)
from app.services.auto_snapshot_service import auto_snapshot_all_portfolios


router = APIRouter(prefix="/snapshots", tags=["snapshots"])


class PnlPoint(BaseModel):
    date: dt.date
    portfolio_value: float
    net_invested: float
    pnl: float
    pnl_pct: float


@router.get("/pnl-curve", response_model=list[PnlPoint])
def pnl_curve(
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils"),
):
    """
    Courbe P&L globale : pour chaque jour où il existe au moins un snapshot,
    retourne la valeur totale des portefeuilles et le montant net investi cumulé.
    P&L = valeur_totale - net_investi.
    """
    from app.repositories.sql_identity_repository import SqlProfileRepository
    from app.domain.trade import TradeType, TradeSide

    snapshot_repo = get_portfolio_snapshot_repo()
    trade_repo = get_trade_repo()

    if profile_id:
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in SqlProfileRepository().list_all()]

    # Agrégation des snapshots par date (somme de tous les portfolios)
    date_values: dict[dt.date, Decimal] = {}
    for pid in profile_ids:
        for snap in snapshot_repo.list(profile_id=pid):
            date_values[snap.date] = date_values.get(snap.date, Decimal("0")) + snap.value.amount

    if not date_values:
        return []

    # Tous les trades TRADE (pas TRANSFER) triés par date
    all_trades = []
    for pid in profile_ids:
        all_trades.extend([
            t for t in trade_repo.list(profile_id=pid)
            if t.trade_type == TradeType.TRADE
        ])
    all_trades.sort(key=lambda t: t.date)

    # Pour chaque date de snapshot, calcule le net investi cumulé
    sorted_dates = sorted(date_values.keys())
    result = []

    for snap_date in sorted_dates:
        net_invested = sum(
            (t.quantity * t.price if t.side == TradeSide.BUY else -(t.quantity * t.price))
            for t in all_trades
            if t.date <= snap_date
        )
        portfolio_value = date_values[snap_date]
        pnl = portfolio_value - net_invested
        pnl_pct = round(float(pnl / net_invested * 100), 2) if net_invested > 0 else 0.0

        result.append(PnlPoint(
            date=snap_date,
            portfolio_value=float(portfolio_value),
            net_invested=float(net_invested),
            pnl=float(pnl),
            pnl_pct=pnl_pct,
        ))

    return result


class DeleteSnapshotsResult(BaseModel):
    portfolio_id: str
    deleted: int


@router.delete("/portfolio/{portfolio_id}", response_model=DeleteSnapshotsResult)
def delete_all_portfolio_snapshots(
    portfolio_id: UUID,
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils"),
):
    """
    Supprime tous les snapshots d'un portefeuille donné.
    Utile avant un re-backfill pour repartir de zéro.
    """
    from app.repositories.sql_identity_repository import SqlProfileRepository

    snapshot_repo = get_portfolio_snapshot_repo()

    if profile_id:
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in SqlProfileRepository().list_all()]

    total_deleted = 0
    for pid in profile_ids:
        total_deleted += snapshot_repo.delete_all(portfolio_id=portfolio_id, profile_id=pid)

    return DeleteSnapshotsResult(portfolio_id=str(portfolio_id), deleted=total_deleted)


class AutoSnapshotResult(BaseModel):
    day: dt.date
    created: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


@router.post("/auto", response_model=AutoSnapshotResult)
def trigger_auto_snapshot(
    day: dt.date | None = Query(default=None, description="UTC day (YYYY-MM-DD), default: today UTC"),
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils"),
):
    """
    Calcule automatiquement la valeur de chaque portefeuille pour un jour donné.
    Si profile_id est absent, tous les profils sont traités.
    """
    from app.repositories.sql_identity_repository import SqlProfileRepository

    if day is None:
        day = dt.datetime.now(dt.timezone.utc).date()

    if profile_id:
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in SqlProfileRepository().list_all()]

    total_created = total_skipped = 0
    all_errors: list[str] = []

    for pid in profile_ids:
        res = auto_snapshot_all_portfolios(
            day=day,
            portfolio_repo=get_portfolio_repo(),
            trade_repo=get_trade_repo(),
            price_repo=get_price_repo(),
            snapshot_repo=get_portfolio_snapshot_repo(),
            profile_id=pid,
        )
        total_created += res["created"]
        total_skipped += res["skipped"]
        all_errors.extend(res["errors"])

    return AutoSnapshotResult(
        day=day,
        created=total_created,
        skipped=total_skipped,
        errors=all_errors,
    )


class BackfillSnapshotsResult(BaseModel):
    date_from: dt.date
    date_to: dt.date
    created: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


@router.post("/backfill", response_model=BackfillSnapshotsResult)
def backfill_snapshots(
    date_from: dt.date = Query(..., description="Start date YYYY-MM-DD"),
    date_to: dt.date = Query(..., description="End date YYYY-MM-DD"),
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils"),
):
    """
    Crée des snapshots quotidiens pour chaque portefeuille sur toute la période.
    Si profile_id est absent, tous les profils sont traités automatiquement.
    """
    from app.repositories.sql_identity_repository import SqlProfileRepository

    total_created = 0
    total_skipped = 0
    all_errors: list[str] = []

    portfolio_repo = get_portfolio_repo()
    trade_repo = get_trade_repo()
    price_repo = get_price_repo()
    snapshot_repo = get_portfolio_snapshot_repo()

    # Détermine la liste des profils à traiter
    if profile_id:
        profile_ids = [profile_id]
    else:
        profile_repo_inst = SqlProfileRepository()
        profile_ids = [p.id for p in profile_repo_inst.list_all()]

    for pid in profile_ids:
        day = date_from
        while day <= date_to:
            res = auto_snapshot_all_portfolios(
                day=day,
                portfolio_repo=portfolio_repo,
                trade_repo=trade_repo,
                price_repo=price_repo,
                snapshot_repo=snapshot_repo,
                profile_id=pid,
            )
            total_created += res["created"]
            total_skipped += res["skipped"]
            all_errors.extend(res["errors"])
            day += dt.timedelta(days=1)

    return BackfillSnapshotsResult(
        date_from=date_from,
        date_to=date_to,
        created=total_created,
        skipped=total_skipped,
        errors=all_errors,
    )
