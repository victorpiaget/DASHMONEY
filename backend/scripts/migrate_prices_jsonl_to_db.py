from __future__ import annotations

import os
from pathlib import Path

from app.settings import get_settings
from app.repositories.jsonl_price_repository import JsonlPriceRepository
from app.repositories.sql_price_repository import SqlPriceRepository


def main() -> int:
    if not os.getenv("DASHMONEY_DATABASE_URL"):
        raise SystemExit("DASHMONEY_DATABASE_URL is required (Postgres URL).")

    settings = get_settings()
    src_path = settings.data_dir / "prices.jsonl"

    src = JsonlPriceRepository(prices_path=src_path)
    dst = SqlPriceRepository()

    items = src.list()
    for p in items:
        dst.add(p)

    print({"migrated": len(items), "from": str(src_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())