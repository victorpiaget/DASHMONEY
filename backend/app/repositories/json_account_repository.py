from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.account import Account
from app.repositories.account_repository import AccountRepository
from app.domain.account import AccountType

class JsonAccountRepository(AccountRepository):
    def __init__(self, *, accounts_path: Path) -> None:
        self._path = accounts_path

    def list_accounts(self) -> list[Account]:
        payload = self._read_accounts_file()
        accounts = payload["accounts"]
        out: list[Account] = []
        seen_ids: set[str] = set()

        for i, acc in enumerate(accounts):
            if not isinstance(acc, dict):
                raise ValueError(f"accounts.json: accounts[{i}] must be an object")

            acc_id = self._require_str(acc, "id", ctx=f"accounts[{i}]").strip()
            if not acc_id:
                raise ValueError(f"accounts.json: accounts[{i}].id cannot be empty")
            if acc_id in seen_ids:
                raise ValueError(f"accounts.json: duplicate account id '{acc_id}'")
            seen_ids.add(acc_id)

            name = self._require_str(acc, "name", ctx=f"accounts[{i}]").strip()
            if not name:
                raise ValueError(f"accounts.json: accounts[{i}].name cannot be empty")

            cur_str = self._require_str(acc, "currency", ctx=f"accounts[{i}]").strip()
            if not cur_str:
                raise ValueError(f"accounts.json: accounts[{i}].currency cannot be empty")
            currency = Currency(cur_str)

            opening_str = self._require_str(acc, "opening_balance", ctx=f"accounts[{i}]").strip()
            opening_balance = SignedMoney.from_str(opening_str, currency)

            opened_on_str = self._require_str(acc, "opened_on", ctx=f"accounts[{i}]").strip()
            opened_on = self._parse_date(opened_on_str, ctx=f"accounts[{i}].opened_on")

            type_str = self._require_str(acc, "account_type", ctx=f"accounts[{i}]").strip()
            if not type_str:
                raise ValueError(f"accounts.json: accounts[{i}].account_type cannot be empty")

            try:
                account_type = AccountType(type_str)
            except Exception:
                raise ValueError(f"accounts.json: accounts[{i}].account_type invalid (got '{type_str}')")

            out.append(
                Account(
                    id=acc_id,
                    name=name,
                    currency=currency,
                    opening_balance=opening_balance,
                    opened_on=opened_on,
                    account_type=account_type,
                )
            )

        return out

    def get_account(self, account_id: str) -> Account:
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("account_id cannot be empty")
        target = account_id.strip()

        for acc in self.list_accounts():
            if acc.id == target:
                return acc

        raise KeyError(f"unknown account_id '{target}'")

    # ---------- helpers ----------
    def _read_accounts_file(self) -> dict:
        if not self._path.exists():
            # STRICT : pas de bootstrap silencieux
            raise FileNotFoundError(f"accounts.json not found at {self._path}")

        raw = self._path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"accounts.json: invalid JSON ({e})") from e

        if not isinstance(payload, dict):
            raise ValueError("accounts.json: root must be an object")

        if payload.get("version") != 1:
            raise ValueError("accounts.json: version must be 1")

        if "accounts" not in payload or not isinstance(payload["accounts"], list):
            raise ValueError("accounts.json: 'accounts' must be a list")

        return payload

    @staticmethod
    def _require_str(obj: dict, key: str, *, ctx: str) -> str:
        if key not in obj:
            raise ValueError(f"accounts.json: {ctx} missing field '{key}'")
        val = obj[key]
        if not isinstance(val, str):
            raise ValueError(f"accounts.json: {ctx}.{key} must be a string")
        return val

    @staticmethod
    def _parse_date(value: str, *, ctx: str) -> dt.date:
        try:
            return dt.date.fromisoformat(value)
        except ValueError as e:
            raise ValueError(f"accounts.json: {ctx} must be ISO date YYYY-MM-DD") from e
    
    def add(self, account: Account) -> None:
        if not isinstance(account, Account):
            raise TypeError("account must be an Account")

        payload = self._read_or_init_accounts_file()
        accounts = payload["accounts"]

        # Unicité id
        for acc in accounts:
            if isinstance(acc, dict) and acc.get("id") == account.id:
                raise ValueError(f"account id '{account.id}' already exists")

        accounts.append(self._to_record(account))
        self._write_accounts_file(payload)


    def _read_or_init_accounts_file(self) -> dict:
        if not self._path.exists():
            # bootstrap contrôlé (pas silencieux côté métier: c'est volontaire ici)
            return {"version": 1, "accounts": []}
        return self._read_accounts_file()


    def _write_accounts_file(self, payload: dict) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self._path)



    def delete(self, *, account_id: str) -> bool:
        if not isinstance(account_id, str) or not account_id.strip():
            return False
        target = account_id.strip()

        payload = self._read_accounts_file()
        accounts = payload["accounts"]

        before = len(accounts)
        accounts2 = [
            a for a in accounts
            if not (isinstance(a, dict) and a.get("id") == target)
        ]

        if len(accounts2) == before:
            return False

        payload["accounts"] = accounts2
        self._write_accounts_file(payload)
        return True


    @staticmethod
    def _to_record(account: Account) -> dict:
        return {
            "id": account.id,
            "name": account.name,
            "currency": account.currency.value,
            "opening_balance": str(account.opening_balance.amount),
            "opened_on": account.opened_on.isoformat(),
            "account_type": account.account_type.value,
        }
