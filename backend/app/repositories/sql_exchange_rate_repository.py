from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db_base import Base
from app.db import new_session


class ExchangeRateRow(Base):
    __tablename__ = "exchange_rates"

    currency: Mapped[str] = mapped_column(String(8), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SqlExchangeRateRepository:
    """Stocke les taux de change avec EUR comme devise de base.
    Convention : rate = nombre d'unités de `currency` pour 1 EUR.
    Ex : USD → 1.08 signifie 1 EUR = 1.08 USD.
    """

    def upsert(self, currency: str, rate: Decimal) -> None:
        with new_session() as s:
            row = s.get(ExchangeRateRow, currency.upper())
            if row is None:
                row = ExchangeRateRow(
                    currency=currency.upper(),
                    rate=rate,
                    updated_at=dt.datetime.now(dt.timezone.utc),
                )
                s.add(row)
            else:
                row.rate = rate
                row.updated_at = dt.datetime.now(dt.timezone.utc)
            s.commit()

    def get_all(self) -> dict[str, float]:
        with new_session() as s:
            rows = s.query(ExchangeRateRow).all()
            return {r.currency: float(r.rate) for r in rows}

    def get(self, currency: str) -> float | None:
        with new_session() as s:
            row = s.get(ExchangeRateRow, currency.upper())
            return float(row.rate) if row else None
