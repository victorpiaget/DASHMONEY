from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from uuid import UUID

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository


class JsonlTransactionRepository(TransactionRepository):
    def __init__(self, *, tx_path: Path, account_repo: AccountRepository) -> None:
        self._path = tx_path
        self._accounts = account_repo

        # Fichier absent => OK (vide)
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    def add(self, tx: Transaction) -> None:
        # Validations cross-file (strict)
        acc = self._accounts.get_account(tx.account_id)
        if tx.amount.currency != acc.currency:
            raise ValueError(
                f"currency mismatch for account '{tx.account_id}': "
                f"tx={tx.amount.currency} account={acc.currency}"
            )

        rec = self._to_record(tx)

        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    def list(self, account_id: str | None = None) -> list[Transaction]:
        txs = self._read_all()

        if account_id is not None:
            aid = account_id.strip()
            txs = [t for t in txs if t.account_id == aid]

        # tri déterministe
        txs.sort(key=lambda t: (t.date, t.sequence))
        return txs

    def get(self, tx_id: UUID) -> Transaction | None:
        for t in self._read_all():
            if t.id == tx_id:
                return t
        return None

    def next_sequence(self, account_id: str, date: dt.date) -> int:
        aid = account_id.strip()
        existing = [t.sequence for t in self._read_all() if t.account_id == aid and t.date == date]
        return (max(existing) + 1) if existing else 1

    # ---------- internals ----------
    def _read_all(self) -> list[Transaction]:
        out: list[Transaction] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    raise ValueError(f"transactions.jsonl line {line_no}: invalid JSON ({e})") from e

                try:
                    tx = self._from_record(data, line_no=line_no)
                except Exception as e:
                    # Strict pratique : stop + ligne fautive
                    raise ValueError(f"transactions.jsonl line {line_no}: {e}") from e

                out.append(tx)

        return out

    def _from_record(self, data: dict, *, line_no: int) -> Transaction:
        if not isinstance(data, dict):
            raise ValueError("record must be an object")

        id_str = self._req_str(data, "id")
        account_id = self._req_str(data, "account_id").strip()
        if not account_id:
            raise ValueError("account_id cannot be empty")

        # compte doit exister (strict)
        acc = self._accounts.get_account(account_id)

        date_str = self._req_str(data, "date")
        date = dt.date.fromisoformat(date_str)

        seq = data.get("sequence")
        if not isinstance(seq, int) or seq < 1:
            raise ValueError("sequence must be int >= 1")

        amount_str = self._req_str(data, "amount")
        currency_str = self._req_str(data, "currency")
        currency = Currency(currency_str)

        # currency doit matcher le compte (strict)
        if currency != acc.currency:
            raise ValueError(f"currency '{currency}' does not match account currency '{acc.currency}'")

        amount = SignedMoney.from_str(amount_str, currency)

        kind_str = self._req_str(data, "kind")
        kind = TransactionKind(kind_str)

        category = self._req_str(data, "category").strip()
        if not category:
            raise ValueError("category cannot be empty")

        subcategory = data.get("subcategory")
        if subcategory is not None:
            if not isinstance(subcategory, str) or not subcategory.strip():
                raise ValueError("subcategory must be null or non-empty string")
            subcategory = subcategory.strip()

        label = data.get("label")
        if label is not None:
            if not isinstance(label, str) or not label.strip():
                raise ValueError("label must be null or non-empty string")
            label = label.strip()

        created_at_str = self._req_str(data, "created_at")
        created_at = dt.datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        transfer_id_raw = data.get("transfer_id")
        if transfer_id_raw is None:
            transfer_id = None
        else:
            if not isinstance(transfer_id_raw, str) or not transfer_id_raw.strip():
                raise ValueError("transfer_id must be null or non-empty string")
            transfer_id = UUID(transfer_id_raw)

        return Transaction.create(
            id=UUID(id_str),
            account_id=account_id,
            date=date,
            sequence=seq,
            amount=amount,
            kind=kind,
            category=category,
            subcategory=subcategory,
            label=label,
            created_at=created_at,
            transfer_id=transfer_id,
        )

    @staticmethod
    def _to_record(tx: Transaction) -> dict:
        return {
            "id": str(tx.id),
            "account_id": tx.account_id,
            "date": tx.date.isoformat(),
            "sequence": tx.sequence,
            "amount": f"{tx.amount.amount:.2f}",
            "currency": tx.amount.currency.value,
            "kind": tx.kind.value,
            "category": tx.category,
            "subcategory": tx.subcategory,
            "label": tx.label,
            "created_at": tx.created_at.isoformat(),
            "transfer_id": str(tx.transfer_id) if tx.transfer_id else None,
        }

    @staticmethod
    def _req_str(d: dict, key: str) -> str:
        if key not in d:
            raise ValueError(f"missing field '{key}'")
        v = d[key]
        if not isinstance(v, str):
            raise ValueError(f"field '{key}' must be a string")
        return v
    def delete(self, *, account_id: str, tx_id: UUID) -> bool:
        aid = account_id.strip()
        if not aid:
            return False

        txs = self._read_all()

        kept: list[Transaction] = []
        deleted = False
        for t in txs:
            if (t.id == tx_id) and (t.account_id == aid) and (not deleted):
                deleted = True
                continue
            kept.append(t)

        if not deleted:
            return False

        # Réécriture complète du fichier (MVP)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8", newline="\n") as f:
            for tx in kept:
                rec = self._to_record(tx)
                line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
                f.write(line + "\n")

        tmp_path.replace(self._path)
        return True
