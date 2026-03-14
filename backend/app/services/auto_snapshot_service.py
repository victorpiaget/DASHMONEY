from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal

from app.domain.money import Currency, Money
from app.domain.portfolio import PortfolioSnapshot
from app.engine.portfolio_positions import compute_positions
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.portfolio_snapshot_repository import PortfolioSnapshotRepository
from app.identity.profile_scope import resolve_profile_id

log = logging.getLogger(__name__)


def auto_snapshot_all_portfolios(
    *,
    day: dt.date,
    portfolio_repo: PortfolioRepository,
    trade_repo: TradeRepository,
    price_repo: PriceRepository,
    snapshot_repo: PortfolioSnapshotRepository,
    profile_id: str | None = None,
) -> dict:
    """
    Pour chaque portefeuille du profil :
      1. Calcule les positions (qty × latest_price_on_or_before(day))
      2. Crée un PortfolioSnapshot si aucun n'existe déjà pour ce portfolio/jour
    Retourne {"day", "created", "skipped", "errors"}
    """
    pid = resolve_profile_id(profile_id)
    portfolios = portfolio_repo.list(profile_id=pid)
    trades = trade_repo.list(profile_id=pid)

    created = 0
    skipped = 0
    errors: list[str] = []

    for portfolio in portfolios:
        existing = snapshot_repo.list(portfolio_id=portfolio.id, profile_id=pid)
        already = any(s.date == day for s in existing)
        if already:
            log.debug("Snapshot already exists for portfolio %s on %s", portfolio.id, day)
            skipped += 1
            continue

        positions = compute_positions(trades=trades, portfolio_id=portfolio.id, as_of=day)

        if not positions:
            log.debug("No positions for portfolio %s on %s — skipping snapshot", portfolio.id, day)
            skipped += 1
            continue

        total = Decimal("0")
        missing_prices: list[str] = []

        for symbol, qty in positions.items():
            pp = price_repo.latest_on_or_before(symbol=symbol, day=day)
            if pp is None:
                log.warning("No price for %s on or before %s — skipping this symbol", symbol, day)
                missing_prices.append(symbol)
                continue
            total += qty * pp.price

        if missing_prices:
            log.warning(
                "Portfolio %s snapshot on %s: missing prices for %s — computed partial value",
                portfolio.id, day, missing_prices,
            )

        note = f"auto — missing: {','.join(missing_prices)}" if missing_prices else "auto"

        try:
            snapshot = PortfolioSnapshot.create(
                portfolio_id=portfolio.id,
                date=day,
                value=Money(amount=total, currency=portfolio.currency),
                note=note,
            )
            snapshot_repo.add(snapshot, profile_id=pid)
            created += 1
            log.info("Snapshot created for portfolio %s on %s: %s %s", portfolio.id, day, total, portfolio.currency)
        except Exception as e:
            log.error("Failed to create snapshot for portfolio %s: %s", portfolio.id, e)
            errors.append(f"{portfolio.id}: {e}")

    return {
        "day": day.isoformat(),
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
