from __future__ import annotations

import datetime as dt

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_user,
    get_portfolio_repo,
    get_trade_repo,
    get_price_repo,
    get_portfolio_snapshot_repo,
    get_profile_repo,
    get_instrument_repo,
    get_request_context,
)
from app.domain.user import User
from app.services.auto_snapshot_service import auto_snapshot_all_portfolios
from app.services.snapshot_recompute_service import recompute_snapshots_from


router = APIRouter(prefix="/snapshots", tags=["snapshots"])


class PnlPoint(BaseModel):
    date: dt.date
    portfolio_value: float
    net_invested: float
    pnl: float
    pnl_pct: float


@router.get("/pnl-curve", response_model=list[PnlPoint])
def pnl_curve(
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils accessibles"),
    user: User = Depends(get_current_user),
):
    """
    Courbe P&L globale : pour chaque jour où il existe au moins un snapshot,
    retourne la valeur totale des portefeuilles et le montant net investi cumulé.
    P&L = valeur_totale - net_investi.
    """
    from app.domain.trade import TradeType, TradeSide

    snapshot_repo = get_portfolio_snapshot_repo()
    trade_repo = get_trade_repo()

    if profile_id:
        if not get_profile_repo().has_profile_access(user_id=user.id, profile_id=profile_id):
            raise HTTPException(status_code=403, detail=f"No access to profile '{profile_id}'")
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in get_profile_repo().list_profiles_for_user(user.id)]

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


class SnapshotPoint(BaseModel):
    date: dt.date
    value: float
    net_invested: float
    pnl: float


class PortfolioCompareItem(BaseModel):
    portfolio_id: str
    portfolio_name: str
    portfolio_type: str
    currency: str
    current_value: float
    net_invested: float
    pnl: float
    pnl_pct: float
    snapshots: list[SnapshotPoint]


@router.get("/compare", response_model=list[PortfolioCompareItem])
def compare_portfolios(
    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),
    ctx=Depends(get_request_context),
) -> list[PortfolioCompareItem]:
    """
    Retourne la performance de chaque portefeuille du profil sur la période.
    Chaque item contient les snapshots (pour le graphique) et les KPIs agrégés.
    """
    from app.domain.trade import TradeType, TradeSide

    portfolio_repo = get_portfolio_repo()
    trade_repo = get_trade_repo()
    snapshot_repo = get_portfolio_snapshot_repo()

    portfolios = portfolio_repo.list(profile_id=ctx.profile_id)
    cutoff = date_to or dt.date.today()
    result = []

    for ptf in portfolios:
        # Snapshots filtrés par période
        if date_from and date_to:
            snaps = snapshot_repo.list_between(
                portfolio_id=ptf.id, date_from=date_from, date_to=date_to,
                profile_id=ctx.profile_id,
            )
        else:
            snaps = snapshot_repo.list(portfolio_id=ptf.id, profile_id=ctx.profile_id)
            if date_from:
                snaps = [s for s in snaps if s.date >= date_from]
            if date_to:
                snaps = [s for s in snaps if s.date <= date_to]

        snaps = sorted(snaps, key=lambda s: s.date)
        if not snaps:
            continue

        current_value = snaps[-1].value.amount

        # Net investi = somme des trades TRADE (pas TRANSFER) jusqu'à cutoff
        trades = [
            t for t in trade_repo.list(portfolio_id=ptf.id, profile_id=ctx.profile_id)
            if t.trade_type == TradeType.TRADE and t.date <= cutoff
        ]
        net_invested = sum(
            (t.quantity * t.price if t.side == TradeSide.BUY else -(t.quantity * t.price))
            for t in trades
        )

        pnl = current_value - net_invested
        pnl_pct = round(float(pnl / net_invested * 100), 2) if net_invested > 0 else 0.0

        # Calcul net_invested cumulatif à chaque date de snapshot (pour la courbe P&L)
        trades_sorted = sorted(trades, key=lambda t: t.date)
        snap_points = []
        for s in snaps:
            ni = sum(
                (t.quantity * t.price if t.side == TradeSide.BUY else -(t.quantity * t.price))
                for t in trades_sorted if t.date <= s.date
            )
            snap_points.append(SnapshotPoint(
                date=s.date,
                value=float(s.value.amount),
                net_invested=float(ni),
                pnl=float(s.value.amount) - float(ni),
            ))

        result.append(PortfolioCompareItem(
            portfolio_id=str(ptf.id),
            portfolio_name=ptf.name,
            portfolio_type=ptf.portfolio_type.value,
            currency=ptf.currency.value,
            current_value=float(current_value),
            net_invested=float(net_invested),
            pnl=float(pnl),
            pnl_pct=pnl_pct,
            snapshots=snap_points,
        ))

    return result


class DeleteSnapshotsResult(BaseModel):
    portfolio_id: str
    deleted: int


@router.delete("/portfolio/{portfolio_id}", response_model=DeleteSnapshotsResult)
def delete_all_portfolio_snapshots(
    portfolio_id: UUID,
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils accessibles"),
    user: User = Depends(get_current_user),
):
    """
    Supprime tous les snapshots d'un portefeuille donné.
    Utile avant un re-backfill pour repartir de zéro.
    """
    snapshot_repo = get_portfolio_snapshot_repo()

    if profile_id:
        if not get_profile_repo().has_profile_access(user_id=user.id, profile_id=profile_id):
            raise HTTPException(status_code=403, detail=f"No access to profile '{profile_id}'")
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in get_profile_repo().list_profiles_for_user(user.id)]

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
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils accessibles"),
    user: User = Depends(get_current_user),
):
    """
    Calcule automatiquement la valeur de chaque portefeuille pour un jour donné.
    Si profile_id est absent, tous les profils accessibles sont traités.
    """
    if day is None:
        day = dt.datetime.now(dt.timezone.utc).date()

    if profile_id:
        if not get_profile_repo().has_profile_access(user_id=user.id, profile_id=profile_id):
            raise HTTPException(status_code=403, detail=f"No access to profile '{profile_id}'")
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in get_profile_repo().list_profiles_for_user(user.id)]

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
    profile_id: str | None = Query(default=None, description="Laisser vide pour tous les profils accessibles"),
    user: User = Depends(get_current_user),
):
    """
    Crée des snapshots quotidiens pour chaque portefeuille sur toute la période.
    Si profile_id est absent, tous les profils accessibles sont traités.
    """
    total_created = 0
    total_skipped = 0
    all_errors: list[str] = []

    portfolio_repo = get_portfolio_repo()
    trade_repo = get_trade_repo()
    price_repo = get_price_repo()
    snapshot_repo = get_portfolio_snapshot_repo()

    # Détermine la liste des profils à traiter
    if profile_id:
        if not get_profile_repo().has_profile_access(user_id=user.id, profile_id=profile_id):
            raise HTTPException(status_code=403, detail=f"No access to profile '{profile_id}'")
        profile_ids = [profile_id]
    else:
        profile_ids = [p.id for p in get_profile_repo().list_profiles_for_user(user.id)]

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


class RecomputeSnapshotsResult(BaseModel):
    portfolio_id: str
    from_date: dt.date
    to_date: dt.date
    deleted: int = Field(ge=0)
    created: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


@router.post("/portfolio/{portfolio_id}/recompute", response_model=RecomputeSnapshotsResult)
def recompute_portfolio_snapshots(
    portfolio_id: UUID,
    from_date: dt.date = Query(..., alias="from", description="Date de départ du recompute (incluse)"),
    ctx=Depends(get_request_context),
):
    """
    Recalcule synchroniquement tous les snapshots d'un portefeuille depuis `from_date`
    jusqu'à aujourd'hui. À utiliser pour réparer des incohérences ou forcer un refresh
    après un import massif.
    """
    if not get_profile_repo().has_profile_access(user_id=ctx.user_id, profile_id=ctx.profile_id):
        raise HTTPException(status_code=403, detail="No access to this profile")

    result = recompute_snapshots_from(
        portfolio_id=portfolio_id,
        from_date=from_date,
        portfolio_repo=get_portfolio_repo(),
        trade_repo=get_trade_repo(),
        price_repo=get_price_repo(),
        snapshot_repo=get_portfolio_snapshot_repo(),
        instrument_repo=get_instrument_repo(),
        profile_id=ctx.profile_id,
    )

    return RecomputeSnapshotsResult(**result)
