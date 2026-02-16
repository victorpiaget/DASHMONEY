from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from uuid import UUID

from app.domain.money import Currency
from app.domain.portfolio import Portfolio, PortfolioType
from app.repositories.portfolio_repository import PortfolioRepository


class JsonPortfolioRepository(PortfolioRepository):
    def __init__(self, *, portfolios_path: Path) -> None:
        self._path = portfolios_path

    def list(self) -> list[Portfolio]:
        payload = self._read_file()
        items = payload["portfolios"]

        out: list[Portfolio] = []
        seen: set[str] = set()

        for i, p in enumerate(items):
            if not isinstance(p, dict):
                raise ValueError(f"portfolios.json: portfolios[{i}] must be an object")

            pid = self._req_str(p, "id", ctx=f"portfolios[{i}]")
            if pid in seen:
                raise ValueError(f"portfolios.json: duplicate id '{pid}'")
            seen.add(pid)

            name = self._req_str(p, "name", ctx=f"portfolios[{i}]").strip()
            cur = Currency(self._req_str(p, "currency", ctx=f"portfolios[{i}]").strip())
            ptype = PortfolioType(self._req_str(p, "portfolio_type", ctx=f"portfolios[{i}]").strip())
            opened_on = dt.date.fromisoformat(self._req_str(p, "opened_on", ctx=f"portfolios[{i}]").strip())
            cash_account_id = p.get("cash_account_id")
            if not isinstance(cash_account_id, str) or not cash_account_id.strip():
                # compat rétro si vieux portfolios.json sans champ
                # on régénère depuis l'UUID du portfolio
                cash_account_id = f"pt_{UUID(pid).hex}_cash"

            out.append(
                Portfolio(
                    id=UUID(pid),
                    name=name,
                    currency=cur,
                    portfolio_type=ptype,
                    opened_on=opened_on,
                    cash_account_id=cash_account_id,
                )
            )
        return out

    def get(self, portfolio_id: UUID) -> Portfolio:
        for p in self.list():
            if p.id == portfolio_id:
                return p
        raise KeyError(f"unknown portfolio_id '{portfolio_id}'")

    def add(self, portfolio: Portfolio) -> None:
        payload = self._read_or_init()
        items = payload["portfolios"]

        if any(isinstance(x, dict) and x.get("id") == str(portfolio.id) for x in items):
            raise ValueError(f"portfolio id '{portfolio.id}' already exists")

        items.append(self._to_record(portfolio))
        self._write(payload)

    def delete(self, *, portfolio_id: UUID) -> bool:
        payload = self._read_or_init()
        items = payload["portfolios"]

        before = len(items)
        items2 = [x for x in items if not (isinstance(x, dict) and x.get("id") == str(portfolio_id))]
        if len(items2) == before:
            return False

        payload["portfolios"] = items2
        self._write(payload)
        return True

    # ---------- internals ----------
    def _read_or_init(self) -> dict:
        if not self._path.exists():
            return {"version": 1, "portfolios": []}
        return self._read_file()

    def _read_file(self) -> dict:
        raw = self._path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"portfolios.json: invalid JSON ({e})") from e

        if not isinstance(payload, dict):
            raise ValueError("portfolios.json: root must be an object")
        if payload.get("version") != 1:
            raise ValueError("portfolios.json: version must be 1")
        if "portfolios" not in payload or not isinstance(payload["portfolios"], list):
            raise ValueError("portfolios.json: 'portfolios' must be a list")

        return payload

    def _write(self, payload: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    def update(
        self,
        *,
        portfolio_id,
        name: str | None = None,
        portfolio_type: PortfolioType | None = None,
    ) -> Portfolio:
        payload = self._read_or_init()   # ✔ méthode existante
        items = payload["portfolios"]   # ✔ clé correcte

        pid = str(portfolio_id)

        for rec in items:
            if isinstance(rec, dict) and str(rec.get("id")) == pid:

                if name is not None:
                    n = name.strip()
                    if not n:
                        raise ValueError("name cannot be empty")
                    rec["name"] = n

                if portfolio_type is not None:
                    rec["portfolio_type"] = portfolio_type.value

                # écriture disque
                self._write(payload)

                # ✔ reconstruction propre via get()
                return self.get(portfolio_id)

        raise KeyError("portfolio not found")

    @staticmethod
    def _req_str(obj: dict, key: str, *, ctx: str) -> str:
        if key not in obj:
            raise ValueError(f"portfolios.json: {ctx} missing field '{key}'")
        v = obj[key]
        if not isinstance(v, str):
            raise ValueError(f"portfolios.json: {ctx}.{key} must be a string")
        return v
    


    @staticmethod
    def _to_record(p: Portfolio) -> dict:
        return {
            "id": str(p.id),
            "name": p.name,
            "currency": p.currency.value,
            "portfolio_type": p.portfolio_type.value,
            "opened_on": p.opened_on.isoformat(),
            "cash_account_id": p.cash_account_id,
        }