from __future__ import annotations

import json
import time
import datetime as dt
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.domain.money import Currency
from app.domain.price_point import PricePoint


# Minimal mapping for common coins. Extend as needed.
_COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "LTC": "litecoin",
}


class CoinGeckoPriceProvider:
    BASE = "https://api.coingecko.com/api/v3/simple/price"

    def __init__(self, *, timeout_sec: int = 15, retries: int = 3, backoff_sec: float = 1.0) -> None:
        self._timeout = timeout_sec
        self._retries = retries
        self._backoff = backoff_sec

    def fetch(self, *, symbol: str, day_utc: dt.date, vs: Currency) -> PricePoint | None:
        sym = symbol.strip().upper()
        cg_id = _COINGECKO_IDS.get(sym)
        if cg_id is None:
            return None

        vs_cur = vs.value.lower()
        params = urlencode({"ids": cg_id, "vs_currencies": vs_cur})
        url = f"{self.BASE}?{params}"

        last_err: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                req = Request(url, headers={"Accept": "application/json", "User-Agent": "dashmoney/0.1"})
                with urlopen(req, timeout=self._timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))

                if cg_id not in payload or vs_cur not in payload[cg_id]:
                    return None

                price = Decimal(str(payload[cg_id][vs_cur]))
                captured_at = dt.datetime.now(dt.timezone.utc)

                return PricePoint(
                    symbol=sym,
                    day=day_utc,
                    price=price,
                    currency=vs,
                    source="coingecko",
                    captured_at=captured_at,
                )
            except Exception as e:
                last_err = e
                time.sleep(self._backoff * attempt)

        return None
