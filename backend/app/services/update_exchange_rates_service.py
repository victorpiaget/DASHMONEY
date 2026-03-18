from __future__ import annotations

import logging
from decimal import Decimal

log = logging.getLogger(__name__)

# Taux EUR → X (1 EUR = X devises)
# Pour les paires forex EURXXX=X yfinance retourne directement "1 EUR = X"
# Pour les crypto XXX-EUR, yfinance retourne "1 XXX = X EUR" → inverse pour obtenir "1 EUR = X XXX"
_FOREX_TICKERS: dict[str, str] = {
    "USD": "EURUSD=X",
    "GBP": "EURGBP=X",
    "JPY": "EURJPY=X",
    "CHF": "EURCHF=X",
    "CAD": "EURCAD=X",
    "AUD": "EURAUD=X",
    "SGD": "EURSGD=X",
}

_CRYPTO_TICKERS: dict[str, str] = {
    "BTC": "BTC-EUR",
    "ETH": "ETH-EUR",
    "USDT": "USDT-EUR",
}


def update_exchange_rates() -> dict:
    """Récupère les taux de change via yfinance et les stocke en base.
    Convention stockée : 1 EUR = rate [currency]
    Retourne {"stored": int, "failed": list[str]}
    """
    from app.repositories.sql_exchange_rate_repository import SqlExchangeRateRepository
    import yfinance as yf

    repo = SqlExchangeRateRepository()

    # EUR est toujours 1.0
    repo.upsert("EUR", Decimal("1.0"))

    stored = 1  # EUR
    failed: list[str] = []

    # Paires forex : EURXXX=X → 1 EUR = X unités
    for currency, ticker in _FOREX_TICKERS.items():
        try:
            data = yf.Ticker(ticker).fast_info
            price = float(data.last_price)
            if price and price > 0:
                repo.upsert(currency, Decimal(str(round(price, 6))))
                stored += 1
                log.info("[exchange_rates] %s = %.6f EUR-based", currency, price)
            else:
                log.warning("[exchange_rates] %s: prix invalide (%s)", currency, price)
                failed.append(currency)
        except Exception as e:
            log.warning("[exchange_rates] Échec fetch %s (%s): %s", currency, ticker, e)
            failed.append(currency)

    # Crypto : XXX-EUR → 1 XXX = X EUR → inverse = 1 EUR = 1/X XXX
    for currency, ticker in _CRYPTO_TICKERS.items():
        try:
            data = yf.Ticker(ticker).fast_info
            price_in_eur = float(data.last_price)
            if price_in_eur and price_in_eur > 0:
                rate = Decimal(str(round(1.0 / price_in_eur, 12)))
                repo.upsert(currency, rate)
                stored += 1
                log.info("[exchange_rates] %s = %.12f (inverse EUR price %.2f)", currency, float(rate), price_in_eur)
            else:
                log.warning("[exchange_rates] %s: prix invalide (%s)", currency, price_in_eur)
                failed.append(currency)
        except Exception as e:
            log.warning("[exchange_rates] Échec fetch %s (%s): %s", currency, ticker, e)
            failed.append(currency)

    return {"stored": stored, "failed": failed}
