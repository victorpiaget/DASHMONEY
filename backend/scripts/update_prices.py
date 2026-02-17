from __future__ import annotations
import os

import datetime as dt

from app.settings import get_settings
from app.repositories.json_instrument_repository import JsonInstrumentRepository
from app.repositories.jsonl_price_repository import JsonlPriceRepository
from app.services.update_prices_service import update_prices_for_day
from app.repositories.sql_price_repository import SqlPriceRepository


def main() -> int:
    settings = get_settings()
    inst_repo = JsonInstrumentRepository(instruments_path=settings.data_dir / "instruments.json")
    if os.getenv("DASHMONEY_DATABASE_URL"):
        price_repo = SqlPriceRepository()
    else:
        price_repo = JsonlPriceRepository(prices_path=settings.data_dir / "prices.jsonl")

    day = dt.datetime.now(dt.timezone.utc).date()
    res = update_prices_for_day(day_utc=day, instrument_repo=inst_repo, price_repo=price_repo)
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
