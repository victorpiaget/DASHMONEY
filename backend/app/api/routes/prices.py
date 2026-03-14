from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_instrument_repo, get_price_repo
from app.api.schemas.prices import PriceOut, PriceUpdateResult, BackfillResult
from app.services.update_prices_service import update_prices_for_day, backfill_prices


router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceOut])
def list_prices(
    symbol: str | None = None,
    date_from: dt.date | None = Query(default=None),
    date_to: dt.date | None = Query(default=None),
):
    repo = get_price_repo()

    if symbol is None:
        if date_from is not None or date_to is not None:
            raise HTTPException(status_code=422, detail="date_from/date_to require symbol")
        return [
            PriceOut(
                symbol=p.symbol,
                day=p.day,
                price=str(p.price),
                currency=p.currency.value,
                source=p.source,
                captured_at=p.captured_at,
            )
            for p in repo.list()
        ]

    if (date_from is None) != (date_to is None):
        raise HTTPException(status_code=422, detail="date_from and date_to must be provided together")

    if date_from is not None and date_to is not None:
        items = repo.list_between(symbol=symbol, date_from=date_from, date_to=date_to)
    else:
        items = repo.list(symbol=symbol)

    return [
        PriceOut(
            symbol=p.symbol,
            day=p.day,
            price=str(p.price),
            currency=p.currency.value,
            source=p.source,
            captured_at=p.captured_at,
        )
        for p in items
    ]


@router.get("/latest-all", response_model=list[PriceOut])
def latest_all_prices():
    """Retourne le dernier prix connu pour chaque instrument."""
    repo = get_price_repo()
    return [
        PriceOut(
            symbol=p.symbol,
            day=p.day,
            price=str(p.price),
            currency=p.currency.value,
            source=p.source,
            captured_at=p.captured_at,
        )
        for p in repo.latest_all()
    ]


@router.get("/{symbol}/latest", response_model=PriceOut)
def latest_price(symbol: str):
    repo = get_price_repo()
    p = repo.latest(symbol=symbol)
    if p is None:
        raise HTTPException(status_code=404, detail="price not found")
    return PriceOut(
        symbol=p.symbol,
        day=p.day,
        price=str(p.price),
        currency=p.currency.value,
        source=p.source,
        captured_at=p.captured_at,
    )


@router.post("/update-daily", response_model=PriceUpdateResult)
def update_daily_prices(day: dt.date | None = Query(default=None, description="UTC day (YYYY-MM-DD), default: today UTC")):
    # default: today UTC
    if day is None:
        day = dt.datetime.now(dt.timezone.utc).date()

    instrument_repo = get_instrument_repo()
    price_repo = get_price_repo()

    res = update_prices_for_day(day_utc=day, instrument_repo=instrument_repo, price_repo=price_repo)

    return PriceUpdateResult(day=dt.date.fromisoformat(res["day"]), stored=res["stored"], skipped=res["skipped"])


@router.post("/backfill", response_model=BackfillResult)
def backfill_prices_route(
    date_from: dt.date = Query(..., description="Start date YYYY-MM-DD"),
    date_to: dt.date = Query(..., description="End date YYYY-MM-DD"),
):
    """
    Fetch full daily price history for all instruments between date_from and date_to.
    Uses yfinance for ETF/STOCK (unlimited), CoinGecko for CRYPTO (~1 year free).
    Existing price points are silently ignored (idempotent).
    """
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to must be >= date_from")

    instrument_repo = get_instrument_repo()
    price_repo = get_price_repo()

    res = backfill_prices(date_from=date_from, date_to=date_to, instrument_repo=instrument_repo, price_repo=price_repo)

    return BackfillResult(
        date_from=dt.date.fromisoformat(res["date_from"]),
        date_to=dt.date.fromisoformat(res["date_to"]),
        stored=res["stored"],
        skipped=res["skipped"],
    )
