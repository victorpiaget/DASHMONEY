from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, String, Numeric, select, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.money import Currency
from app.domain.trade import Trade, TradeSide
from app.repositories.trade_repository import TradeRepository


class TradeRow(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day: Mapped[dt.date] = mapped_column("date", Date, index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    instrument_symbol: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("instruments.symbol", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    linked_cash_tx_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )


class SqlTradeRepository(TradeRepository):

    def __init__(self) -> None:
        init_db()

    # -------- add --------

    def add(self, trade: Trade) -> None:
        with new_session() as s:
            if s.get(TradeRow, str(trade.id)) is not None:
                raise ValueError(f"trade {trade.id} already exists")

            s.add(self._to_row(trade))
            s.commit()

    # -------- list --------

    def list(self, *, portfolio_id: UUID | None = None) -> list[Trade]:
        with new_session() as s:
            stmt = select(TradeRow)
            if portfolio_id is not None:
                stmt = stmt.where(TradeRow.portfolio_id == str(portfolio_id))

            rows = s.execute(stmt).scalars().all()
            trades = [self._to_domain(r) for r in rows]
            trades.sort(key=lambda t: (t.date, str(t.id)))  # align JSONL :contentReference[oaicite:5]{index=5}
            return trades

    def list_between(self, *, portfolio_id: UUID, date_from: dt.date, date_to: dt.date) -> list[Trade]:
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")

        with new_session() as s:
            stmt = (
                select(TradeRow)
                .where(TradeRow.portfolio_id == str(portfolio_id))
                .where(TradeRow.day >= date_from)
                .where(TradeRow.day <= date_to)
            )

            rows = s.execute(stmt).scalars().all()
            trades = [self._to_domain(r) for r in rows]
            trades.sort(key=lambda t: (t.date, str(t.id)))
            return trades

    # -------- get --------

    def get(self, trade_id: UUID) -> Trade:
        with new_session() as s:
            row = s.get(TradeRow, str(trade_id))
            if row is None:
                raise KeyError("trade not found")
            return self._to_domain(row)

    # -------- delete (physique en SQL) --------

    def delete(self, *, trade_id: UUID) -> bool:
        with new_session() as s:
            row = s.get(TradeRow, str(trade_id))
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    # -------- update (remplace JSONL merge) --------

    def update(self, *, trade_id: UUID, patch: dict) -> Trade:
        with new_session() as s:
            row = s.get(TradeRow, str(trade_id))
            if row is None:
                raise KeyError("trade not found")

            # Appliquer patch comme JSONL _merge :contentReference[oaicite:6]{index=6}
            if "date" in patch:
                row.day = patch["date"]
            if "side" in patch:
                row.side = patch["side"].value
            if "quantity" in patch:
                row.quantity = Decimal(str(patch["quantity"]))
            if "price" in patch:
                row.price = Decimal(str(patch["price"]))
            if "fees" in patch:
                row.fees = Decimal(str(patch["fees"]))
            if "label" in patch:
                row.label = patch["label"]
            if "linked_cash_tx_id" in patch:
                row.linked_cash_tx_id = str(patch["linked_cash_tx_id"]) if patch["linked_cash_tx_id"] else None
            if "currency" in patch:
                row.currency = patch["currency"].value

            s.commit()
            s.refresh(row)
            return self._to_domain(row)

    # -------- mapping --------

    @staticmethod
    def _to_row(t: Trade) -> TradeRow:
        return TradeRow(
            id=str(t.id),
            portfolio_id=str(t.portfolio_id),
            day=t.date,
            side=t.side.value,
            instrument_symbol=t.instrument_symbol.upper(),
            quantity=Decimal(str(t.quantity)),
            price=Decimal(str(t.price)),
            fees=Decimal(str(t.fees)),
            currency=t.currency.value,
            label=t.label,
            linked_cash_tx_id=str(t.linked_cash_tx_id) if t.linked_cash_tx_id else None,
        )

    @staticmethod
    def _to_domain(r: TradeRow) -> Trade:
        return Trade.create(
            id=UUID(r.id),
            portfolio_id=UUID(r.portfolio_id),
            date=r.day,
            side=TradeSide(r.side),
            instrument_symbol=r.instrument_symbol,
            quantity=r.quantity,
            price=r.price,
            fees=r.fees,
            currency=Currency(r.currency),
            label=r.label,
            linked_cash_tx_id=UUID(r.linked_cash_tx_id) if r.linked_cash_tx_id else None,
        )
