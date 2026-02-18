from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import Date, String, select, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.money import Currency
from app.domain.portfolio import Portfolio, PortfolioType
from app.repositories.portfolio_repository import PortfolioRepository


class PortfolioRow(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    portfolio_type: Mapped[str] = mapped_column(String(32), nullable=False)
    opened_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    cash_account_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )



class SqlPortfolioRepository(PortfolioRepository):

    def __init__(self) -> None:
        init_db()

    # -------- list --------

    def list(self) -> list[Portfolio]:
        with new_session() as s:
            rows = s.execute(select(PortfolioRow)).scalars().all()
            return [self._to_domain(r) for r in rows]

    # -------- get --------

    def get(self, portfolio_id: UUID) -> Portfolio:
        with new_session() as s:
            row = s.get(PortfolioRow, str(portfolio_id))
            if row is None:
                raise KeyError(f"unknown portfolio_id '{portfolio_id}'")
            return self._to_domain(row)

    # -------- add --------

    def add(self, portfolio: Portfolio) -> None:
        with new_session() as s:
            if s.get(PortfolioRow, str(portfolio.id)) is not None:
                raise ValueError(f"portfolio id '{portfolio.id}' already exists")

            s.add(self._to_row(portfolio))
            s.commit()

    # -------- delete --------

    def delete(self, *, portfolio_id: UUID) -> bool:
        with new_session() as s:
            row = s.get(PortfolioRow, str(portfolio_id))
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    # -------- update (présent dans JSON repo) --------

    def update(
        self,
        *,
        portfolio_id: UUID,
        name: str | None = None,
        portfolio_type: PortfolioType | None = None,
    ) -> Portfolio:

        with new_session() as s:
            row = s.get(PortfolioRow, str(portfolio_id))
            if row is None:
                raise KeyError("portfolio not found")

            if name is not None:
                n = name.strip()
                if not n:
                    raise ValueError("name cannot be empty")
                row.name = n

            if portfolio_type is not None:
                row.portfolio_type = portfolio_type.value

            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    # -------- mapping --------

    @staticmethod
    def _to_row(p: Portfolio) -> PortfolioRow:
        return PortfolioRow(
            id=str(p.id),
            name=p.name,
            currency=p.currency.value,
            portfolio_type=p.portfolio_type.value,
            opened_on=p.opened_on,
            cash_account_id=p.cash_account_id,
        )

    @staticmethod
    def _to_domain(r: PortfolioRow) -> Portfolio:
        return Portfolio(
            id=UUID(r.id),
            name=r.name,
            currency=Currency(r.currency),
            portfolio_type=PortfolioType(r.portfolio_type),
            opened_on=r.opened_on,
            cash_account_id=r.cash_account_id,
        )
