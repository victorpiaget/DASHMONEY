from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from uuid import UUID

from app.domain.money import Currency, Money
from app.domain.portfolio import PortfolioSnapshot
from app.repositories.portfolio_snapshot_repository import PortfolioSnapshotRepository


class JsonlPortfolioSnapshotRepository(PortfolioSnapshotRepository):
    def __init__(self, *, snapshots_path: Path) -> None:
        self._path = snapshots_path

        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    def add(self, snapshot: PortfolioSnapshot) -> None:
        rec = self._to_record(snapshot)
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    def list(self, portfolio_id: UUID | None = None) -> list[PortfolioSnapshot]:
        snaps = self._read_all()
        if portfolio_id is not None:
            snaps = [s for s in snaps if s.portfolio_id == portfolio_id]
        snaps.sort(key=lambda s: (s.date, str(s.id)))
        return snaps

    def list_between(self, *, portfolio_id: UUID, date_from: dt.date, date_to: dt.date) -> list[PortfolioSnapshot]:
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")
        snaps = [s for s in self.list(portfolio_id=portfolio_id) if date_from <= s.date <= date_to]
        snaps.sort(key=lambda s: (s.date, str(s.id)))
        return snaps

    # ---------- internals ----------
    def _read_all(self) -> list[PortfolioSnapshot]:
        out: list[PortfolioSnapshot] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    raise ValueError(f"portfolio_snapshots.jsonl line {line_no}: invalid JSON ({e})") from e

                try:
                    out.append(self._from_record(data))
                except Exception as e:
                    raise ValueError(f"portfolio_snapshots.jsonl line {line_no}: {e}") from e

        return out

    @staticmethod
    def _from_record(d: dict) -> PortfolioSnapshot:
        if not isinstance(d, dict):
            raise ValueError("record must be an object")

        sid = UUID(_req_str(d, "id"))
        pid = UUID(_req_str(d, "portfolio_id"))
        date = dt.date.fromisoformat(_req_str(d, "date"))
        amount_str = _req_str(d, "value")
        currency = Currency(_req_str(d, "currency"))

        value = Money.from_str(amount_str, currency)
        note = d.get("note")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise ValueError("note must be null or non-empty string")

        return PortfolioSnapshot(
            id=sid,
            portfolio_id=pid,
            date=date,
            value=value,
            note=note.strip() if isinstance(note, str) else None,
        )

    @staticmethod
    def _to_record(s: PortfolioSnapshot) -> dict:
        return {
            "id": str(s.id),
            "portfolio_id": str(s.portfolio_id),
            "date": s.date.isoformat(),
            "value": f"{s.value.amount:.2f}",
            "currency": s.value.currency.value,
            "note": s.note,
        }


def _req_str(d: dict, key: str) -> str:
    if key not in d:
        raise ValueError(f"missing field '{key}'")
    v = d[key]
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"field '{key}' must be a non-empty string")
    return v.strip()