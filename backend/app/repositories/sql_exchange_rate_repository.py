from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Numeric, String, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.db_base import Base
from app.db import new_session
from app.db_types import UtcDateTime


class ExchangeRateRow(Base):
    __tablename__ = "exchange_rates"

    currency: Mapped[str] = mapped_column(String(8), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        UtcDateTime(),
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
        """
        Upsert tolérant aux courses : SELECT-then-INSERT/UPDATE peut échouer
        si un autre thread (scheduler vs requête, ou test reset) insère entre
        nos deux étapes. En cas d'IntegrityError, on retombe sur un UPDATE.
        """
        currency_norm = currency.upper()
        with new_session() as s:
            row = s.get(ExchangeRateRow, currency_norm)
            if row is None:
                try:
                    s.add(
                        ExchangeRateRow(
                            currency=currency_norm,
                            rate=rate,
                            updated_at=dt.datetime.now(dt.timezone.utc),
                        )
                    )
                    s.commit()
                    return
                except IntegrityError:
                    s.rollback()
                    row = s.get(ExchangeRateRow, currency_norm)
                    if row is None:
                        # Cas extrême : ligne supprimée entre l'INSERT raté
                        # et notre re-fetch ; on abandonne plutôt que boucler.
                        return
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
