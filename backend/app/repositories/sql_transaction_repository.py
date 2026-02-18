from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Integer, Numeric, String, select, func
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository


class TransactionRow(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    day: Mapped[dt.date] = mapped_column("date", Date, index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    transfer_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)


class SqlTransactionRepository(TransactionRepository):

    def __init__(self, *, tx_account_repo: AccountRepository) -> None:
        self._accounts = tx_account_repo
        init_db()

    def add(self, tx: Transaction) -> None:
        acc = self._accounts.get_account(tx.account_id)
        if tx.amount.currency != acc.currency:
            raise ValueError(
                f"currency mismatch for account '{tx.account_id}': "
                f"tx={tx.amount.currency} account={acc.currency}"
            )

        with new_session() as s:
            existing = s.get(TransactionRow, str(tx.id))
            if existing is not None:
                raise ValueError(f"Transaction with id {tx.id} already exists")

            s.add(self._to_row(tx))
            s.commit()

    def list(self, account_id: str | None = None) -> list[Transaction]:
        with new_session() as s:
            stmt = select(TransactionRow)
            if account_id is not None:
                aid = account_id.strip()
                stmt = stmt.where(TransactionRow.account_id == aid)

            rows = s.execute(stmt).scalars().all()
            txs = [self._to_domain(r) for r in rows]
            txs.sort(key=lambda t: (t.date, t.sequence))
            return txs

    def get(self, tx_id: UUID) -> Transaction | None:
        with new_session() as s:
            row = s.get(TransactionRow, str(tx_id))
            return self._to_domain(row) if row else None

    def next_sequence(self, account_id: str, date: dt.date) -> int:
        aid = account_id.strip()
        with new_session() as s:
            return self._next_sequence_in_session(s, account_id=aid, date=date)

    def delete(self, *, account_id: str, tx_id: UUID) -> bool:
        aid = account_id.strip()
        if not aid:
            return False

        with new_session() as s:
            row = s.get(TransactionRow, str(tx_id))
            if row is None:
                return False
            if row.account_id != aid:
                return False

            s.delete(row)
            s.commit()
            return True

    def update(
        self,
        *,
        account_id: str,
        tx_id: UUID,
        category: str | None = None,
        subcategory: str | None = None,
        label: str | None = None,
        date: dt.date | None = None,
        amount: SignedMoney | None = None,
        kind: TransactionKind | None = None,
    ) -> Transaction:
        aid = account_id.strip()
        if not aid:
            raise ValueError("account_id cannot be empty")

        with new_session() as s:
            row = s.get(TransactionRow, str(tx_id))
            if row is None or row.account_id != aid:
                raise KeyError("Transaction not found")

            if row.kind == TransactionKind.TRANSFER.value or row.transfer_id is not None:
                raise ValueError("Transfers must be updated via /transfers endpoint")

            if date is not None and date != row.day:
                row.sequence = self._next_sequence_in_session(s, account_id=aid, date=date)
                row.day = date

            if kind is not None:
                if kind == TransactionKind.TRANSFER:
                    raise ValueError("Cannot set kind to TRANSFER via transaction PATCH")
                row.kind = kind.value

            if amount is not None:
                acc = self._accounts.get_account(aid)
                if amount.currency != acc.currency:
                    raise ValueError(
                        f"currency mismatch for account '{aid}': "
                        f"tx={amount.currency} account={acc.currency}"
                    )
                row.amount = Decimal(str(amount.amount))
                row.currency = amount.currency.value

            if category is not None:
                c = category.strip()
                if not c:
                    raise ValueError("category cannot be empty")
                row.category = c

            if subcategory is not None:
                sc = subcategory.strip()
                if not sc:
                    raise ValueError("subcategory must be null or non-empty string")
                row.subcategory = sc

            if label is not None:
                lb = label.strip()
                if not lb:
                    raise ValueError("label must be null or non-empty string")
                row.label = lb

            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    def update_transfer(
        self,
        *,
        transfer_id: UUID,
        new_date: dt.date | None = None,
        new_amount_pos: SignedMoney | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        label: str | None = None,
    ) -> tuple[Transaction, Transaction]:
        with new_session() as s:
            tid = str(transfer_id)
            rows = s.execute(
                select(TransactionRow).where(TransactionRow.transfer_id == tid)
            ).scalars().all()
            if len(rows) != 2:
                raise KeyError("Transfer not found")

            for r in rows:
                if r.kind != TransactionKind.TRANSFER.value:
                    raise ValueError("Invalid transfer: legs must be TRANSFER")

            tx1 = self._to_domain(rows[0])
            tx2 = self._to_domain(rows[1])

            tx_from, tx_to = tx1, tx2
            if tx_from.amount.amount > 0 and tx_to.amount.amount < 0:
                tx_from, tx_to = tx_to, tx_from

            if tx_from.amount.amount >= 0 or tx_to.amount.amount <= 0:
                raise ValueError("Invalid transfer: expected one negative and one positive amount")

            row_from = s.get(TransactionRow, str(tx_from.id))
            row_to = s.get(TransactionRow, str(tx_to.id))
            assert row_from is not None and row_to is not None

            if new_date is not None:
                if new_date != row_from.day:
                    row_from.sequence = self._next_sequence_in_session(
                        s, account_id=row_from.account_id, date=new_date
                    )
                if new_date != row_to.day:
                    row_to.sequence = self._next_sequence_in_session(
                        s, account_id=row_to.account_id, date=new_date
                    )
                row_from.day = new_date
                row_to.day = new_date

            if new_amount_pos is not None:
                if new_amount_pos.amount <= 0:
                    raise ValueError("amount must be > 0")

                acc_from = self._accounts.get_account(row_from.account_id)
                acc_to = self._accounts.get_account(row_to.account_id)
                if (
                    new_amount_pos.currency != acc_from.currency
                    or new_amount_pos.currency != acc_to.currency
                ):
                    raise ValueError("Currency mismatch in transfer update")

                row_to.amount = Decimal(str(new_amount_pos.amount))
                row_to.currency = new_amount_pos.currency.value
                row_from.amount = Decimal(str(-new_amount_pos.amount))
                row_from.currency = new_amount_pos.currency.value

            def pick(old: str | None, new: str | None, field: str) -> str | None:
                if new is None:
                    return old
                s2 = new.strip()
                if not s2:
                    raise ValueError(f"{field} must be null or non-empty string")
                return s2

            row_from.category = pick(row_from.category, category, "category") or row_from.category
            row_to.category = pick(row_to.category, category, "category") or row_to.category
            row_from.subcategory = pick(row_from.subcategory, subcategory, "subcategory")
            row_to.subcategory = pick(row_to.subcategory, subcategory, "subcategory")
            row_from.label = pick(row_from.label, label, "label")
            row_to.label = pick(row_to.label, label, "label")

            s.commit()
            s.refresh(row_from)
            s.refresh(row_to)

            return self._to_domain(row_from), self._to_domain(row_to)

    def delete_transfer(self, *, transfer_id: UUID) -> tuple[UUID, UUID]:
        with new_session() as s:
            tid = str(transfer_id)
            rows = s.execute(
                select(TransactionRow).where(TransactionRow.transfer_id == tid)
            ).scalars().all()
            if len(rows) != 2:
                raise KeyError("Transfer not found")

            for r in rows:
                if r.kind != TransactionKind.TRANSFER.value:
                    raise ValueError("Invalid transfer: legs must be TRANSFER")

            id1 = UUID(rows[0].id)
            id2 = UUID(rows[1].id)

            s.delete(rows[0])
            s.delete(rows[1])
            s.commit()
            return id1, id2

    @staticmethod
    def _next_sequence_in_session(s: Session, *, account_id: str, date: dt.date) -> int:
        stmt = (
            select(func.max(TransactionRow.sequence))
            .where(TransactionRow.account_id == account_id)
            .where(TransactionRow.day == date)
        )
        max_seq = s.execute(stmt).scalar_one_or_none()
        return int(max_seq or 0) + 1

    @staticmethod
    def _to_row(tx: Transaction) -> TransactionRow:
        return TransactionRow(
            id=str(tx.id),
            account_id=tx.account_id,
            day=tx.date,
            sequence=tx.sequence,
            amount=Decimal(str(tx.amount.amount)),
            currency=tx.amount.currency.value,
            kind=tx.kind.value,
            category=tx.category,
            subcategory=tx.subcategory,
            label=tx.label,
            created_at=tx.created_at,
            transfer_id=str(tx.transfer_id) if tx.transfer_id else None,
        )

    @staticmethod
    def _to_domain(row: TransactionRow) -> Transaction:
        currency = Currency(row.currency)
        amount = SignedMoney(amount=row.amount, currency=currency)
        return Transaction.create(
            id=UUID(row.id),
            account_id=row.account_id,
            date=row.day,
            sequence=row.sequence,
            amount=amount,
            kind=TransactionKind(row.kind),
            category=row.category,
            subcategory=row.subcategory,
            label=row.label,
            created_at=row.created_at,
            transfer_id=UUID(row.transfer_id) if row.transfer_id else None,
        )
