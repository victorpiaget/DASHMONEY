from __future__ import annotations

import json
from pathlib import Path

from app.domain.instrument import Instrument, InstrumentKind
from app.domain.money import Currency
from app.repositories.instrument_repository import InstrumentRepository


class JsonInstrumentRepository(InstrumentRepository):
    def __init__(self, *, instruments_path: Path) -> None:
        self._path = instruments_path

    def list(self) -> list[Instrument]:
        payload = self._read_or_init()
        items = payload["instruments"]
        out: list[Instrument] = []
        seen: set[str] = set()

        for i, it in enumerate(items):
            if not isinstance(it, dict):
                raise ValueError(f"instruments.json: instruments[{i}] must be an object")

            sym = self._req_str(it, "symbol", ctx=f"instruments[{i}]").strip().upper()
            if not sym:
                raise ValueError("symbol cannot be empty")
            if sym in seen:
                raise ValueError(f"duplicate symbol '{sym}'")
            seen.add(sym)

            kind = InstrumentKind(self._req_str(it, "kind", ctx=f"instruments[{i}]").strip())
            cur = Currency(self._req_str(it, "currency", ctx=f"instruments[{i}]").strip())

            out.append(Instrument(symbol=sym, kind=kind, currency=cur))

        return out

    def get(self, symbol: str) -> Instrument:
        sym = symbol.strip().upper()
        for it in self.list():
            if it.symbol == sym:
                return it
        raise KeyError(f"unknown instrument symbol '{sym}'")

    def add(self, instrument: Instrument) -> None:
        payload = self._read_or_init()
        items = payload["instruments"]
        sym = instrument.symbol.strip().upper()

        if any(isinstance(x, dict) and str(x.get("symbol", "")).upper() == sym for x in items):
            raise ValueError(f"instrument '{sym}' already exists")

        items.append(
            {
                "symbol": sym,
                "kind": instrument.kind.value,
                "currency": instrument.currency.value,
            }
        )
        self._write(payload)

    def delete(self, *, symbol: str) -> bool:
        payload = self._read_or_init()
        items = payload["instruments"]
        sym = symbol.strip().upper()

        before = len(items)
        items2 = [x for x in items if not (isinstance(x, dict) and str(x.get("symbol", "")).upper() == sym)]
        if len(items2) == before:
            return False

        payload["instruments"] = items2
        self._write(payload)
        return True

    # -------- internals --------
    def _read_or_init(self) -> dict:
        if not self._path.exists():
            return {"version": 1, "instruments": []}
        raw = self._path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("instruments.json: root must be an object")
        if payload.get("version") != 1:
            raise ValueError("instruments.json: version must be 1")
        if "instruments" not in payload or not isinstance(payload["instruments"], list):
            raise ValueError("instruments.json: 'instruments' must be a list")
        return payload

    def _write(self, payload: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    @staticmethod
    def _req_str(obj: dict, key: str, *, ctx: str) -> str:
        if key not in obj:
            raise ValueError(f"instruments.json: {ctx} missing field '{key}'")
        v = obj[key]
        if not isinstance(v, str):
            raise ValueError(f"instruments.json: {ctx}.{key} must be a string")
        return v