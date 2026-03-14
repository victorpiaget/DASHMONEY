from __future__ import annotations

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.instrument import Instrument, InstrumentKind
from app.domain.money import Currency
from app.repositories.instrument_repository import InstrumentRepository


class InstrumentRow(Base):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")
    ticker: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")


class SqlInstrumentRepository(InstrumentRepository):

    def __init__(self) -> None:
        init_db()

    def list(self) -> list[Instrument]:
        with new_session() as s:
            rows = s.execute(select(InstrumentRow)).scalars().all()
            return [self._to_domain(r) for r in rows]

    def get(self, symbol: str) -> Instrument:
        sym = symbol.strip().upper()
        with new_session() as s:
            row = s.get(InstrumentRow, sym)
            if row is None:
                raise KeyError(f"unknown instrument symbol '{sym}'")
            return self._to_domain(row)

    def add(self, instrument: Instrument) -> None:
        sym = instrument.symbol.strip().upper()

        with new_session() as s:
            existing = s.get(InstrumentRow, sym)
            if existing is not None:
                raise ValueError(f"instrument '{sym}' already exists")

            row = InstrumentRow(
                symbol=sym,
                kind=instrument.kind.value,
                currency=instrument.currency.value,
                name=instrument.name or "",
                ticker=instrument.ticker or "",
            )
            s.add(row)
            s.commit()

    def update(self, symbol: str, instrument: Instrument) -> Instrument:
        sym = symbol.strip().upper()
        with new_session() as s:
            row = s.get(InstrumentRow, sym)
            if row is None:
                raise KeyError(f"instrument '{sym}' not found")
            row.kind = instrument.kind.value
            row.currency = instrument.currency.value
            row.name = instrument.name or ""
            row.ticker = instrument.ticker or ""
            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    def delete(self, *, symbol: str) -> bool:
        sym = symbol.strip().upper()
        with new_session() as s:
            row = s.get(InstrumentRow, sym)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    @staticmethod
    def _to_domain(row: InstrumentRow) -> Instrument:
        return Instrument(
            symbol=row.symbol,
            kind=InstrumentKind(row.kind),
            currency=Currency(row.currency),
            name=row.name or "",
            ticker=row.ticker or "",
        )
