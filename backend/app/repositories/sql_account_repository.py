from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, select, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.account import Account, AccountType
from app.domain.money import Currency
from app.domain.signed_money import SignedMoney
from app.repositories.account_repository import AccountRepository
from app.identity.defaults import DEFAULT_PROFILE_ID
from app.repositories.sql_identity_models import ProfileRow  # noqa: F401



class AccountRow(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    opened_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )


class SqlAccountRepository(AccountRepository):
    """
    SQL implementation aligned with JsonAccountRepository behavior:
    - list_accounts(): returns all accounts
    - get_account(): raises KeyError if unknown
    - add(): raises ValueError if id exists
    - delete(): returns False if unknown/invalid id
    - update(): parity method (exists in JsonAccountRepository)
    """

    def __init__(self) -> None:
        init_db()

    def list_accounts(self) -> list[Account]:
        with new_session() as s:
            rows = s.execute(
                select(AccountRow)
                .where(AccountRow.profile_id == DEFAULT_PROFILE_ID)
                .order_by(AccountRow.id.asc())
            ).scalars().all()

            return [self._to_domain(r) for r in rows]

    def get_account(self, account_id: str) -> Account:
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("account_id cannot be empty")
        target = account_id.strip()

        with new_session() as s:
            row = s.get(AccountRow, target)
            if row is None or row.profile_id != DEFAULT_PROFILE_ID:
                raise KeyError(f"unknown account_id '{target}'")
            return self._to_domain(row)

    def add(self, account: Account) -> None:
        if not isinstance(account, Account):
            raise TypeError("account must be an Account")

        with new_session() as s:
            existing = s.get(AccountRow, account.id)
            if existing is not None:
                raise ValueError(f"account id '{account.id}' already exists")

            row = AccountRow(
                id=account.id,
                name=account.name,
                currency=account.currency.value,
                opening_balance=Decimal(str(account.opening_balance.amount)),
                opened_on=account.opened_on,
                account_type=account.account_type.value,
                profile_id=DEFAULT_PROFILE_ID,
            )
            s.add(row)
            s.commit()

    def delete(self, *, account_id: str) -> bool:
        if not isinstance(account_id, str) or not account_id.strip():
            return False
        target = account_id.strip()

        with new_session() as s:
            row = s.get(AccountRow, target)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def update(
        self,
        *,
        account_id: str,
        name: str | None = None,
        account_type: AccountType | None = None,
    ) -> Account:
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("account_id cannot be empty")
        target = account_id.strip()

        with new_session() as s:
            row = s.get(AccountRow, target)
            if row is None:
                raise KeyError(f"unknown account_id '{target}'")

            if name is not None:
                n = name.strip()
                if not n:
                    raise ValueError("name cannot be empty")
                row.name = n

            if account_type is not None:
                row.account_type = account_type.value

            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: AccountRow) -> Account:
        currency = Currency(row.currency)
        opening = SignedMoney(
            amount=row.opening_balance,
            currency=currency,
        )
        return Account(
            id=row.id,
            name=row.name,
            currency=currency,
            opening_balance=opening,
            opened_on=row.opened_on,
            account_type=AccountType(row.account_type),
            
        )
