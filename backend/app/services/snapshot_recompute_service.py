from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from uuid import UUID

from app.domain.money import Money
from app.domain.portfolio import PortfolioSnapshot
from app.engine.portfolio_positions import compute_positions
from app.identity.profile_scope import resolve_profile_id
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.portfolio_snapshot_repository import PortfolioSnapshotRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.trade_repository import TradeRepository
from app.services.update_prices_service import backfill_prices

log = logging.getLogger(__name__)


def recompute_snapshots_from(
    *,
    portfolio_id: UUID,
    from_date: dt.date,
    portfolio_repo: PortfolioRepository,
    trade_repo: TradeRepository,
    price_repo: PriceRepository,
    snapshot_repo: PortfolioSnapshotRepository,
    instrument_repo: InstrumentRepository,
    profile_id: str | None = None,
    today: dt.date | None = None,
) -> dict:
    """
    Recalcule l'intégralité des snapshots d'un portefeuille depuis from_date
    (inclus) jusqu'à aujourd'hui.

    Étapes :
      1. Supprime les snapshots existants >= from_date
      2. Assure la présence des prix historiques sur la plage via yfinance/Binance
         (backfill global idempotent — les doublons sont ignorés)
      3. Reconstruit un snapshot par jour : positions(as_of=day) × prix jour

    Idempotent : peut être appelé plusieurs fois de suite sans effet de bord
    (sauf la charge réseau du backfill de prix).
    """
    pid = resolve_profile_id(profile_id)
    today = today or dt.datetime.now(dt.timezone.utc).date()

    if from_date > today:
        return {
            "portfolio_id": str(portfolio_id),
            "from_date": from_date.isoformat(),
            "to_date": today.isoformat(),
            "deleted": 0,
            "created": 0,
            "skipped": 0,
            "errors": ["from_date is in the future"],
        }

    try:
        portfolio = portfolio_repo.get(portfolio_id, profile_id=pid)
    except KeyError:
        return {
            "portfolio_id": str(portfolio_id),
            "from_date": from_date.isoformat(),
            "to_date": today.isoformat(),
            "deleted": 0,
            "created": 0,
            "skipped": 0,
            "errors": ["portfolio not found"],
        }

    # 1. Suppression des snapshots existants à partir de from_date
    deleted = snapshot_repo.delete_from(
        portfolio_id=portfolio_id,
        from_date=from_date,
        profile_id=pid,
    )
    log.info(
        "recompute: deleted %d snapshots for portfolio %s from %s",
        deleted, portfolio_id, from_date,
    )

    # 2. Backfill des prix historiques sur la plage — idempotent (doublons ignorés
    #    par price_repo.add). Si la plage est déjà en base, c'est un no-op côté DB.
    try:
        backfill_prices(
            date_from=from_date,
            date_to=today,
            instrument_repo=instrument_repo,
            price_repo=price_repo,
        )
    except Exception as e:
        log.warning("recompute: price backfill failed (continuing with existing prices): %s", e)

    # 3. Reconstruction jour par jour
    trades = trade_repo.list(profile_id=pid)
    created = 0
    skipped = 0
    errors: list[str] = []

    day = from_date
    while day <= today:
        positions = compute_positions(
            trades=trades,
            portfolio_id=portfolio_id,
            as_of=day,
        )

        if not positions:
            # Portefeuille vide ce jour-là — pas de snapshot (cohérent avec auto_snapshot_service)
            skipped += 1
            day += dt.timedelta(days=1)
            continue

        total = Decimal("0")
        missing: list[str] = []

        for symbol, qty in positions.items():
            pp = price_repo.latest_on_or_before(symbol=symbol, day=day)
            if pp is None:
                missing.append(symbol)
                continue
            total += qty * pp.price

        if missing and total == Decimal("0"):
            # Tous les prix sont manquants : pas de snapshot (valeur 0 serait trompeuse)
            skipped += 1
            day += dt.timedelta(days=1)
            continue

        if missing:
            log.warning(
                "recompute: portfolio %s on %s missing prices for %s — partial value",
                portfolio_id, day, missing,
            )

        note = f"recompute — missing: {','.join(missing)}" if missing else "recompute"

        try:
            snap = PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                date=day,
                value=Money(amount=total, currency=portfolio.currency),
                note=note,
            )
            snapshot_repo.add(snap, profile_id=pid)
            created += 1
        except Exception as e:
            log.error("recompute: failed to create snapshot %s / %s: %s", portfolio_id, day, e)
            errors.append(f"{day.isoformat()}: {e}")

        day += dt.timedelta(days=1)

    log.info(
        "recompute: portfolio %s [%s → %s] deleted=%d created=%d skipped=%d errors=%d",
        portfolio_id, from_date, today, deleted, created, skipped, len(errors),
    )

    return {
        "portfolio_id": str(portfolio_id),
        "from_date": from_date.isoformat(),
        "to_date": today.isoformat(),
        "deleted": deleted,
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
