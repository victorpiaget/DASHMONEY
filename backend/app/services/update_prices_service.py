from __future__ import annotations

import datetime as dt
import logging

from app.domain.instrument import InstrumentKind
from app.domain.money import Currency
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.price_repository import PriceRepository
from app.providers.coingecko_provider import CoinGeckoPriceProvider
from app.providers.stooq_provider import StooqEodPriceProvider


log = logging.getLogger(__name__)


def update_prices_for_day(
    *,
    day_utc: dt.date,
    instrument_repo: InstrumentRepository,
    price_repo: PriceRepository,
    timeout_sec: int = 15,
    retries: int = 3,
    backoff_sec: float = 1.0,
) -> dict:
    cg = CoinGeckoPriceProvider(timeout_sec=timeout_sec, retries=retries, backoff_sec=backoff_sec)
    stooq = StooqEodPriceProvider(timeout_sec=timeout_sec, retries=retries, backoff_sec=backoff_sec)

    stored = 0
    skipped = 0

    for inst in instrument_repo.list():
        sym = inst.symbol.strip().upper()

        if inst.kind == InstrumentKind.CRYPTO:
            pp = cg.fetch(symbol=sym, day_utc=day_utc, vs=inst.currency)
            if pp is None:
                skipped += 1
                continue
            price_repo.add(pp)
            stored += 1
            continue

        if inst.kind in (InstrumentKind.STOCK, InstrumentKind.ETF):
            pp = stooq.fetch(symbol=sym, day_utc=day_utc, currency=inst.currency)
            if pp is None:
                skipped += 1
                continue
            price_repo.add(pp)
            stored += 1
            continue

        # OTHER: ignore
        skipped += 1

    return {"day": day_utc.isoformat(), "stored": stored, "skipped": skipped}
