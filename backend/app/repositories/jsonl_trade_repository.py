from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from uuid import UUID
from decimal import Decimal

from app.domain.money import Currency
from app.domain.trade import Trade, TradeSide
from app.repositories.trade_repository import TradeRepository


class JsonlTradeRepository(TradeRepository):
    def __init__(self, *, trades_path: Path) -> None:
        self._path = trades_path
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    def add(self, trade: Trade) -> None:
        rec = self._to_record(trade)
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    def list(self, *, portfolio_id: UUID | None = None) -> list[Trade]:
        trades = self._read_all()
        if portfolio_id is not None:
            trades = [t for t in trades if t.portfolio_id == portfolio_id]
        trades.sort(key=lambda t: (t.date, str(t.id)))
        return trades

    def list_between(self, *, portfolio_id: UUID, date_from: dt.date, date_to: dt.date) -> list[Trade]:
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")
        trades = [t for t in self.list(portfolio_id=portfolio_id) if date_from <= t.date <= date_to]
        trades.sort(key=lambda t: (t.date, str(t.id)))
        return trades

    def get(self, trade_id: UUID) -> Trade:
        for t in self._read_all():
            if t.id == trade_id:
                return t
        raise KeyError("trade not found")

    def delete(self, *, trade_id: UUID) -> bool:
        # JSONL: delete logique (tombstone)
        try:
            self.get(trade_id)
        except KeyError:
            return False
        tomb = {"_deleted": True, "id": str(trade_id)}
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(tomb, ensure_ascii=False, separators=(",", ":")) + "\n")
        return True

    def update(self, *, trade_id: UUID, patch: dict) -> Trade:
        # JSONL: append new version with same id
        base = self.get(trade_id)
        merged = self._merge(base, patch)
        self.add(merged)
        return merged

    # -------- internals --------
    def _read_all(self) -> list[Trade]:
        latest: dict[str, Trade] = {}
        deleted: set[str] = set()

        with self._path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("_deleted") is True:
                    tid = str(data.get("id", "")).strip()
                    if tid:
                        deleted.add(tid)
                        latest.pop(tid, None)
                    continue

                t = self._from_record(data)
                latest[str(t.id)] = t

        # remove deleted
        for tid in deleted:
            latest.pop(tid, None)

        return list(latest.values())

    @staticmethod
    def _from_record(d: dict) -> Trade:
        if not isinstance(d, dict):
            raise ValueError("record must be an object")

        tid = UUID(_req_str(d, "id"))
        pid = UUID(_req_str(d, "portfolio_id"))
        date = dt.date.fromisoformat(_req_str(d, "date"))
        side = TradeSide(_req_str(d, "side"))
        symbol = _req_str(d, "instrument_symbol").strip().upper()

        qty = Decimal(_req_str(d, "quantity"))
        price = Decimal(_req_str(d, "price"))
        fees = Decimal(_req_str(d, "fees"))
        cur = Currency(_req_str(d, "currency"))

        label = d.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            label = None

        linked = d.get("linked_cash_tx_id")
        linked_id = UUID(linked) if isinstance(linked, str) and linked.strip() else None

        return Trade(
            id=tid,
            portfolio_id=pid,
            date=date,
            side=side,
            instrument_symbol=symbol,
            quantity=qty,
            price=price,
            fees=fees,
            currency=cur,
            label=label.strip() if isinstance(label, str) else None,
            linked_cash_tx_id=linked_id,
        )

    @staticmethod
    def _to_record(t: Trade) -> dict:
        return {
            "id": str(t.id),
            "portfolio_id": str(t.portfolio_id),
            "date": t.date.isoformat(),
            "side": t.side.value,
            "instrument_symbol": t.instrument_symbol.upper(),
            "quantity": str(t.quantity),
            "price": str(t.price),
            "fees": str(t.fees),
            "currency": t.currency.value,
            "label": t.label,
            "linked_cash_tx_id": str(t.linked_cash_tx_id) if t.linked_cash_tx_id else None,
        }

    @staticmethod
    def _merge(base: Trade, patch: dict) -> Trade:
        # patch keys: date, side, instrument_symbol, quantity, price, fees, label
        return Trade.create(
            id=base.id,
            portfolio_id=base.portfolio_id,
            date=patch.get("date", base.date),
            side=patch.get("side", base.side),
            instrument_symbol=patch.get("instrument_symbol", base.instrument_symbol),
            quantity=patch.get("quantity", base.quantity),
            price=patch.get("price", base.price),
            fees=patch.get("fees", base.fees),
            currency=patch.get("currency", base.currency),
            label=patch.get("label", base.label),
            linked_cash_tx_id=patch.get("linked_cash_tx_id", base.linked_cash_tx_id),
        )


def _req_str(d: dict, key: str) -> str:
    if key not in d:
        raise ValueError(f"missing field '{key}'")
    v = d[key]
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"field '{key}' must be a non-empty string")
    return v.strip()