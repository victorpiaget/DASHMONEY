from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db import init_db, new_session
from app.domain.money import Currency
from app.domain.price_point import PricePoint
from app.repositories.price_repository import PriceRepository


class Base(DeclarativeBase):
    pass


class PricePointRow(Base):
    __tablename__ = "price_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    day: Mapped[dt.date] = mapped_column(Date, index=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)


class SqlPriceRepository(PriceRepository):
    def __init__(self) -> None:
        # ensure tables exist (V1 simple). Later we can move to migrations.
        init_db()

    def add(self, price: PricePoint) -> None:
        row = PricePointRow(
            symbol=price.symbol.strip().upper(),
            day=price.day,
            price=price.price,
            currency=price.currency.value,
            source=price.source,
            captured_at=price.captured_at,
        )
        with new_session() as s:
            s.add(row)
            s.commit()

    def list(self, *, symbol: str | None = None) -> list[PricePoint]:
        stmt = select(PricePointRow)
        if symbol is not None:
            stmt = stmt.where(PricePointRow.symbol == symbol.strip().upper())
        stmt = stmt.order_by(PricePointRow.symbol, PricePointRow.day, PricePointRow.captured_at)

        with new_session() as s:
            rows = s.execute(stmt).scalars().all()

        return [self._to_domain(r) for r in rows]

    def list_between(self, *, symbol: str, date_from: dt.date, date_to: dt.date) -> list[PricePoint]:
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")

        sym = symbol.strip().upper()
        stmt = (
            select(PricePointRow)
            .where(PricePointRow.symbol == sym)
            .where(PricePointRow.day >= date_from)
            .where(PricePointRow.day <= date_to)
            .order_by(PricePointRow.day, PricePointRow.captured_at)
        )

        with new_session() as s:
            rows = s.execute(stmt).scalars().all()

        return [self._to_domain(r) for r in rows]

    def latest(self, *, symbol: str) -> PricePoint | None:
        sym = symbol.strip().upper()
        stmt = (
            select(PricePointRow)
            .where(PricePointRow.symbol == sym)
            .order_by(PricePointRow.day.desc(), PricePointRow.captured_at.desc())
            .limit(1)
        )

        with new_session() as s:
            row = s.execute(stmt).scalars().first()

        return None if row is None else self._to_domain(row)

    @staticmethod
    def _to_domain(r: PricePointRow) -> PricePoint:
        return PricePoint(
            symbol=r.symbol,
            day=r.day,
            price=Decimal(r.price),
            currency=Currency(r.currency),
            source=r.source,
            captured_at=r.captured_at,
        )