from __future__ import annotations

import csv
import io
import time
import datetime as dt
from decimal import Decimal
from urllib.request import Request, urlopen

from app.domain.money import Currency
from app.domain.price_point import PricePoint


class StooqEodPriceProvider:
    def __init__(self, *, timeout_sec: int = 15, retries: int = 3, backoff_sec: float = 1.0) -> None:
        self._timeout = timeout_sec
        self._retries = retries
        self._backoff = backoff_sec

    def fetch(self, *, symbol: str, day_utc: dt.date, currency: Currency) -> PricePoint | None:
        sym = symbol.strip().upper()
        for stooq_sym in _candidate_stooq_symbols(sym):
            pp = self._fetch_one(symbol=sym, stooq_symbol=stooq_sym, day_utc=day_utc, currency=currency)
            if pp is not None:
                return pp
        return None

    def _fetch_one(self, *, symbol: str, stooq_symbol: str, day_utc: dt.date, currency: Currency) -> PricePoint | None:
        url = f"https://stooq.com/q/l/?s={stooq_symbol.lower()}&i=d"

        for attempt in range(1, self._retries + 1):
            try:
                req = Request(url, headers={"User-Agent": "dashmoney/0.1"})
                with urlopen(req, timeout=self._timeout) as resp:
                    text = resp.read().decode("utf-8", errors="replace")

                reader = csv.DictReader(io.StringIO(text))
                rows = list(reader)
                if not rows:
                    return None

                row = rows[-1]
                close_str = row.get("Close") or row.get("close")
                if close_str is None:
                    return None
                close_str = close_str.strip()
                if not close_str or close_str in ("N/A", "-"):
                    return None

                price = Decimal(close_str)
                captured_at = dt.datetime.now(dt.timezone.utc)
                return PricePoint(
                    symbol=symbol,
                    day=day_utc,
                    price=price,
                    currency=currency,
                    source="stooq",
                    captured_at=captured_at,
                )
            except Exception:
                time.sleep(self._backoff * attempt)

        return None


def _candidate_stooq_symbols(symbol: str) -> list[str]:
    # If user already provides a suffix (e.g. AAPL.US), try as-is first.
    if "." in symbol:
        return [symbol]

    # Best-effort suffix guesses. Extend later with an explicit mapping if needed.
    return [
        symbol,
        f"{symbol}.US",
        f"{symbol}.FR",
        f"{symbol}.PA",
        f"{symbol}.DE",
    ]
