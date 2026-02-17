from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from decimal import Decimal

from app.domain.money import Currency
from app.domain.price_point import PricePoint
from app.repositories.price_repository import PriceRepository


class JsonlPriceRepository(PriceRepository):
    def __init__(self, *, prices_path: Path) -> None:
        self._path = prices_path
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    def add(self, price: PricePoint) -> None:
        rec = self._to_record(price)
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    def list(self, *, symbol: str | None = None) -> list[PricePoint]:
        items = self._read_all()
        if symbol is not None:
            s = symbol.strip().upper()
            items = [p for p in items if p.symbol == s]
        items.sort(key=lambda p: (p.symbol, p.day, p.captured_at))
        return items

    def list_between(self, *, symbol: str, date_from: dt.date, date_to: dt.date) -> list[PricePoint]:
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")
        s = symbol.strip().upper()
        items = [p for p in self._read_all() if p.symbol == s and date_from <= p.day <= date_to]
        items.sort(key=lambda p: (p.day, p.captured_at))
        return items

    def latest(self, *, symbol: str) -> PricePoint | None:
        s = symbol.strip().upper()
        best: PricePoint | None = None
        for p in self._read_all():
            if p.symbol != s:
                continue
            if best is None or (p.day, p.captured_at) > (best.day, best.captured_at):
                best = p
        return best

    # -------- internals --------
    def _read_all(self) -> list[PricePoint]:
        out: list[PricePoint] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                try:
                    out.append(self._from_record(data))
                except Exception as e:
                    raise ValueError(f"prices.jsonl: invalid record at line {line_no}: {e}") from e
        return out

    @staticmethod
    def _from_record(d: dict) -> PricePoint:
        if not isinstance(d, dict):
            raise ValueError("record must be an object")

        sym = _req_str(d, "symbol").strip().upper()
        day = dt.date.fromisoformat(_req_str(d, "day"))
        price = Decimal(_req_str(d, "price"))
        cur = Currency(_req_str(d, "currency"))
        source = _req_str(d, "source")
        captured_at = dt.datetime.fromisoformat(_req_str(d, "captured_at"))
        if captured_at.tzinfo is None:
            # tolerate naive by assuming UTC
            captured_at = captured_at.replace(tzinfo=dt.timezone.utc)

        return PricePoint(
            symbol=sym,
            day=day,
            price=price,
            currency=cur,
            source=source,
            captured_at=captured_at,
        )

    @staticmethod
    def _to_record(p: PricePoint) -> dict:
        return {
            "symbol": p.symbol.strip().upper(),
            "day": p.day.isoformat(),
            "price": str(p.price),
            "currency": p.currency.value,
            "source": p.source,
            "captured_at": p.captured_at.isoformat(),
        }


def _req_str(d: dict, key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"missing/invalid '{key}'")
    return v
