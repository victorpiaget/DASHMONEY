from __future__ import annotations

import datetime as dt
import logging

from app.domain.instrument import InstrumentKind
from app.domain.money import Currency
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.price_repository import PriceRepository
from app.providers.coingecko_provider import CoinGeckoPriceProvider
from app.providers.yfinance_provider import YFinancePriceProvider


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
    """Fetch closing prices for all instruments for a given day and store them."""
    cg = CoinGeckoPriceProvider(timeout_sec=timeout_sec, retries=retries, backoff_sec=backoff_sec)
    yf = YFinancePriceProvider()

    stored = 0
    skipped = 0

    for inst in instrument_repo.list():
        sym = inst.symbol.strip().upper()

        if inst.kind == InstrumentKind.CRYPTO:
            pp = cg.fetch(symbol=sym, day_utc=day_utc, vs=inst.currency)
            if pp is None:
                log.warning("No CoinGecko price for %s on %s", sym, day_utc)
                skipped += 1
                continue
            price_repo.add(pp)
            stored += 1
            continue

        if inst.kind in (InstrumentKind.STOCK, InstrumentKind.ETF):
            pp = yf.fetch(symbol=sym, ticker=inst.ticker, day_utc=day_utc, currency=inst.currency)
            if pp is None:
                log.warning("No yfinance price for %s (ticker=%s) on %s", sym, inst.ticker or sym, day_utc)
                skipped += 1
                continue
            price_repo.add(pp)
            stored += 1
            continue

        # OTHER: ignore
        skipped += 1

    return {"day": day_utc.isoformat(), "stored": stored, "skipped": skipped}


def backfill_prices(
    *,
    date_from: dt.date,
    date_to: dt.date,
    instrument_repo: InstrumentRepository,
    price_repo: PriceRepository,
) -> dict:
    """
    Fetch full daily price history for all instruments between date_from and date_to.
    Uses yfinance (unlimited history) for ETF/STOCK.
    Uses CoinGecko free historical API for CRYPTO (up to ~365 days).
    """
    cg = CoinGeckoPriceProvider()
    yf_provider = YFinancePriceProvider()

    stored = 0
    skipped = 0

    for inst in instrument_repo.list():
        sym = inst.symbol.strip().upper()

        if inst.kind == InstrumentKind.CRYPTO:
            # Priorité : Binance Klines (gratuit, sans clé) → fallback CoinGecko
            points = _binance_klines_history(sym, date_from, date_to, inst.currency)
            if not points:
                log.info("Binance klines empty for %s, trying CoinGecko", sym)
                points = _coingecko_history(sym, date_from, date_to, inst.currency, cg)
            for pp in points:
                try:
                    price_repo.add(pp)
                    stored += 1
                except Exception:
                    pass  # duplicate — ignore
            if not points:
                log.warning("No crypto history for %s (tried Binance + CoinGecko)", sym)
                skipped += 1
            continue

        if inst.kind in (InstrumentKind.STOCK, InstrumentKind.ETF):
            points = yf_provider.fetch_history(
                symbol=sym, ticker=inst.ticker,
                date_from=date_from, date_to=date_to,
                currency=inst.currency,
            )
            for pp in points:
                try:
                    price_repo.add(pp)
                    stored += 1
                except Exception:
                    pass  # duplicate — ignore
            if not points:
                log.warning("No yfinance history for %s (ticker=%s)", sym, inst.ticker or sym)
                skipped += 1
            continue

        skipped += 1

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "stored": stored,
        "skipped": skipped,
    }


def _coingecko_history(
    symbol: str,
    date_from: dt.date,
    date_to: dt.date,
    currency: Currency,
    cg: CoinGeckoPriceProvider,
) -> list:
    """
    Fetch daily historical prices from CoinGecko free API.
    Uses /coins/{id}/market_chart/range endpoint.
    Free tier: limited to ~1 year of daily data per call.
    """
    import json
    import time
    from decimal import Decimal
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from app.domain.price_point import PricePoint

    # Reuse the symbol→id mapping from the provider
    from app.providers.coingecko_provider import _COINGECKO_IDS
    cg_id = _COINGECKO_IDS.get(symbol.upper())
    if cg_id is None:
        return []

    vs = currency.value.lower()
    ts_from = int(dt.datetime.combine(date_from, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    ts_to = int(dt.datetime.combine(date_to, dt.time.max, tzinfo=dt.timezone.utc).timestamp())
    params = urlencode({"vs_currency": vs, "from": ts_from, "to": ts_to})
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart/range?{params}"

    for attempt in range(1, 4):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "dashmoney/0.1"})
            with urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            prices_raw = payload.get("prices", [])
            captured_at = dt.datetime.now(dt.timezone.utc)
            points = []
            seen_days: set[dt.date] = set()

            for ts_ms, price_val in prices_raw:
                day = dt.datetime.fromtimestamp(ts_ms / 1000, tz=dt.timezone.utc).date()
                if day in seen_days:
                    continue
                seen_days.add(day)
                points.append(PricePoint(
                    symbol=symbol.upper(),
                    day=day,
                    price=Decimal(str(price_val)),
                    currency=currency,
                    source="coingecko_history",
                    captured_at=captured_at,
                ))

            return points

        except Exception as e:
            log.warning("CoinGecko history attempt %d failed for %s: %s", attempt, symbol, e)
            time.sleep(2 * attempt)

    return []


# Mapping symbol → Binance pair suffix (quote currency)
_BINANCE_QUOTE: dict[str, str] = {
    "EUR": "EUR",
    "USD": "USDT",
    "USDT": "USDT",
    "BTC": "BTC",
    "ETH": "ETH",
}


def _binance_klines_history(
    symbol: str,
    date_from: dt.date,
    date_to: dt.date,
    currency: Currency,
) -> list:
    """
    Fetch daily closing prices from Binance public klines API.
    No API key required. Pairs: DOGEEUR, XRPEUR, SOLEUR, BNBEUR, etc.
    Falls back silently if pair does not exist on Binance.
    """
    import json
    import time
    from decimal import Decimal
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from app.domain.price_point import PricePoint

    quote = _BINANCE_QUOTE.get(currency.value.upper(), "EUR")
    pair = f"{symbol.upper()}{quote}"

    ts_from = int(dt.datetime.combine(date_from, dt.time.min, tzinfo=dt.timezone.utc).timestamp() * 1000)
    ts_to = int(dt.datetime.combine(date_to, dt.time.max, tzinfo=dt.timezone.utc).timestamp() * 1000)

    points: list = []
    captured_at = dt.datetime.now(dt.timezone.utc)

    # Binance limits 1000 klines per call — paginate
    current_start = ts_from
    for _ in range(20):  # max 20 pages = ~5.5 years of daily data
        params = urlencode({
            "symbol": pair,
            "interval": "1d",
            "startTime": current_start,
            "endTime": ts_to,
            "limit": 1000,
        })
        url = f"https://api.binance.com/api/v3/klines?{params}"

        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": "dashmoney/0.1"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data or isinstance(data, dict):  # error response
                break

            for candle in data:
                # [open_time, open, high, low, close, ...]
                open_time_ms = candle[0]
                close_price = candle[4]
                day = dt.datetime.fromtimestamp(open_time_ms / 1000, tz=dt.timezone.utc).date()
                points.append(PricePoint(
                    symbol=symbol.upper(),
                    day=day,
                    price=Decimal(str(close_price)),
                    currency=currency,
                    source="binance_klines",
                    captured_at=captured_at,
                ))

            if len(data) < 1000:
                break  # last page

            # Next page starts after the last candle's open time
            current_start = data[-1][0] + 1

        except Exception as e:
            log.warning("Binance klines failed for %s: %s", pair, e)
            break

    return points
