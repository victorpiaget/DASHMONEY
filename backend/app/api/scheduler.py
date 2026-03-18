from __future__ import annotations

import datetime as dt
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    """
    Exécuté chaque jour à 20h UTC :
      1. Fetch les prix du jour (toutes les sources)
      2. Crée les snapshots automatiques pour tous les profils
    """
    from app.api.deps import (
        get_instrument_repo,
        get_price_repo,
        get_portfolio_repo,
        get_trade_repo,
        get_portfolio_snapshot_repo,
    )
    from app.services.update_prices_service import update_prices_for_day
    from app.services.auto_snapshot_service import auto_snapshot_all_portfolios
    from app.repositories.sql_identity_repository import SqlProfileRepository

    today = dt.datetime.now(dt.timezone.utc).date()
    log.info("[scheduler] Daily job starting for %s", today)

    # 1. Mise à jour des taux de change
    try:
        from app.services.update_exchange_rates_service import update_exchange_rates
        fx_result = update_exchange_rates()
        log.info("[scheduler] Exchange rates updated: %s stored, %s failed", fx_result["stored"], fx_result["failed"])
    except Exception as e:
        log.error("[scheduler] Exchange rate update failed: %s", e)

    # 2. Mise à jour des prix
    try:
        result = update_prices_for_day(
            day_utc=today,
            instrument_repo=get_instrument_repo(),
            price_repo=get_price_repo(),
        )
        log.info("[scheduler] Prices updated: %s stored, %s skipped", result["stored"], result["skipped"])
    except Exception as e:
        log.error("[scheduler] Price update failed: %s", e)

    # 2. Snapshots pour tous les profils
    try:
        profile_repo = SqlProfileRepository()
        profiles = profile_repo.list_all()
        for profile in profiles:
            res = auto_snapshot_all_portfolios(
                day=today,
                portfolio_repo=get_portfolio_repo(),
                trade_repo=get_trade_repo(),
                price_repo=get_price_repo(),
                snapshot_repo=get_portfolio_snapshot_repo(),
                profile_id=profile.id,
            )
            log.info(
                "[scheduler] Profile %s — snapshots: %s created, %s skipped",
                profile.id, res["created"], res["skipped"],
            )
            if res["errors"]:
                log.warning("[scheduler] Snapshot errors for profile %s: %s", profile.id, res["errors"])
    except Exception as e:
        log.error("[scheduler] Snapshot job failed: %s", e)

    log.info("[scheduler] Daily job done")


def _catchup_job() -> None:
    """
    Exécuté une fois au démarrage dans un thread background.
    Rattrape tous les jours manquants depuis le dernier snapshot connu.
    """
    from app.db import new_session
    from sqlalchemy import text
    from app.api.deps import (
        get_instrument_repo,
        get_price_repo,
        get_portfolio_repo,
        get_trade_repo,
        get_portfolio_snapshot_repo,
    )
    from app.services.update_prices_service import backfill_prices
    from app.services.auto_snapshot_service import auto_snapshot_all_portfolios
    from app.repositories.sql_identity_repository import SqlProfileRepository

    today = dt.datetime.now(dt.timezone.utc).date()

    # 0. Taux de change au démarrage si absents
    try:
        from app.services.update_exchange_rates_service import update_exchange_rates
        from app.repositories.sql_exchange_rate_repository import SqlExchangeRateRepository
        if len(SqlExchangeRateRepository().get_all()) <= 1:
            fx = update_exchange_rates()
            log.info("[catchup] Taux de change initialisés: %s stored, %s failed", fx["stored"], fx["failed"])
    except Exception as e:
        log.error("[catchup] Initialisation taux de change échouée: %s", e)

    # Trouve le dernier jour snapshottté toutes tables confondues
    with new_session() as s:
        row = s.execute(text("SELECT MAX(date) FROM portfolio_snapshots")).fetchone()
    last_snapshot: dt.date | None = row[0] if row and row[0] else None

    if last_snapshot is None:
        log.info("[catchup] Aucun snapshot en base — pas de rattrapage au démarrage")
        return

    if last_snapshot >= today:
        log.info("[catchup] Snapshots à jour (dernier : %s)", last_snapshot)
        return

    date_from = last_snapshot + dt.timedelta(days=1)
    log.info("[catchup] Rattrapage %s → %s", date_from, today)

    # 1. Backfill prix manquants
    try:
        result = backfill_prices(
            date_from=date_from,
            date_to=today,
            instrument_repo=get_instrument_repo(),
            price_repo=get_price_repo(),
        )
        log.info("[catchup] Prix : %s stored, %s skipped", result["stored"], result["skipped"])
    except Exception as e:
        log.error("[catchup] Backfill prix échoué : %s", e)

    # 2. Backfill snapshots jour par jour
    try:
        profiles = SqlProfileRepository().list_all()
        total_created = 0
        day = date_from
        while day <= today:
            for profile in profiles:
                res = auto_snapshot_all_portfolios(
                    day=day,
                    portfolio_repo=get_portfolio_repo(),
                    trade_repo=get_trade_repo(),
                    price_repo=get_price_repo(),
                    snapshot_repo=get_portfolio_snapshot_repo(),
                    profile_id=profile.id,
                )
                total_created += res["created"]
            day += dt.timedelta(days=1)
        log.info("[catchup] Snapshots créés : %s", total_created)
    except Exception as e:
        log.error("[catchup] Backfill snapshots échoué : %s", e)

    log.info("[catchup] Rattrapage terminé")


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    # Chaque jour à 20h UTC
    _scheduler.add_job(_daily_job, CronTrigger(hour=20, minute=0, timezone="UTC"), id="daily_prices_snapshots")
    _scheduler.start()
    # Rattrapage des jours manquants au démarrage (thread background)
    threading.Thread(target=_catchup_job, daemon=True, name="catchup").start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
