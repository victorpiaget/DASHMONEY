from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal

from app.domain.money import Currency
from app.domain.price_point import PricePoint

log = logging.getLogger(__name__)


class YFinancePriceProvider:
    """
    Fetches end-of-day prices via yfinance (Yahoo Finance).
    Covers ETF, stocks (US, EU, FR), and crypto pairs.

    Uses instrument.ticker if set (e.g. "PAEEM.PA"),
    falls back to instrument.symbol (e.g. "AAPL").
    """

    def fetch(self, *, symbol: str, ticker: str, day_utc: dt.date, currency: Currency) -> PricePoint | None:
        try:
            import yfinance as yf  # imported lazily — not mandatory at startup
        except ImportError:
            log.error("yfinance not installed — run: poetry add yfinance")
            return None

        target = ticker.strip() if ticker.strip() else symbol.strip().upper()

        try:
            # Download a 5-day window to handle weekends / market holidays
            date_from = day_utc - dt.timedelta(days=7)
            date_to = day_utc + dt.timedelta(days=1)

            hist = yf.download(
                target,
                start=date_from.isoformat(),
                end=date_to.isoformat(),
                progress=False,
                auto_adjust=True,
            )

            if hist is None or hist.empty:
                log.warning("yfinance: no data for %s", target)
                return None

            # Most recent closing price on or before day_utc
            hist.index = hist.index.normalize()
            available = hist[hist.index.date <= day_utc]
            if available.empty:
                return None

            close = available["Close"].iloc[-1]
            # yf.download returns a DataFrame; close may be a Series if multiple tickers
            if hasattr(close, "iloc"):
                close = close.iloc[0]

            price = Decimal(str(float(close)))
            if price <= 0:
                return None

            return PricePoint(
                symbol=symbol.strip().upper(),
                day=day_utc,
                price=price,
                currency=currency,
                source="yfinance",
                captured_at=dt.datetime.now(dt.timezone.utc),
            )

        except Exception as e:
            log.warning("yfinance fetch failed for %s: %s", target, e)
            return None

    def fetch_history(
        self,
        *,
        symbol: str,
        ticker: str,
        date_from: dt.date,
        date_to: dt.date,
        currency: Currency,
    ) -> list[PricePoint]:
        """Fetch all daily closing prices between date_from and date_to."""
        try:
            import yfinance as yf
        except ImportError:
            log.error("yfinance not installed")
            return []

        target = ticker.strip() if ticker.strip() else symbol.strip().upper()

        try:
            hist = yf.download(
                target,
                start=date_from.isoformat(),
                end=(date_to + dt.timedelta(days=1)).isoformat(),
                progress=False,
                auto_adjust=True,
            )

            if hist is None or hist.empty:
                return []

            points: list[PricePoint] = []
            captured_at = dt.datetime.now(dt.timezone.utc)

            for idx, row in hist.iterrows():
                day = idx.date() if hasattr(idx, "date") else idx
                close = row["Close"]
                if hasattr(close, "item"):
                    close = close.item()
                price = Decimal(str(float(close)))
                if price <= 0:
                    continue
                points.append(PricePoint(
                    symbol=symbol.strip().upper(),
                    day=day,
                    price=price,
                    currency=currency,
                    source="yfinance",
                    captured_at=captured_at,
                ))

            return points

        except Exception as e:
            log.warning("yfinance history failed for %s: %s", target, e)
            return []
