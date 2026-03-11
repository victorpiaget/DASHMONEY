from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Numeric, String, select, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.money import Currency, Money
from app.domain.portfolio import PortfolioSnapshot
from app.repositories.portfolio_snapshot_repository import PortfolioSnapshotRepository
from app.identity.profile_scope import resolve_profile_id
from app.repositories.sql_identity_models import ProfileRow  # noqa: F401



class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    day: Mapped[dt.date] = mapped_column("date", Date, index=True, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )


class SqlPortfolioSnapshotRepository(PortfolioSnapshotRepository):

    def __init__(self) -> None:
        init_db()

    def add(self, snapshot: PortfolioSnapshot, *, profile_id: str | None = None) -> None:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            if s.get(PortfolioSnapshotRow, str(snapshot.id)) is not None:
                raise ValueError(f"snapshot id '{snapshot.id}' already exists")

            row = self._to_row(snapshot, pid)
            s.add(row)
            s.commit()

    def list(self, portfolio_id: UUID | None = None, *, profile_id: str | None = None) -> list[PortfolioSnapshot]:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            stmt = select(PortfolioSnapshotRow)
            stmt = stmt.where(PortfolioSnapshotRow.profile_id == pid)

            if portfolio_id is not None:
                stmt = stmt.where(PortfolioSnapshotRow.portfolio_id == str(portfolio_id))

            rows = s.execute(stmt).scalars().all()
            snaps = [self._to_domain(r) for r in rows]
            snaps.sort(key=lambda s2: (s2.date, str(s2.id)))  # align JSONL :contentReference[oaicite:5]{index=5}
            return snaps

    def list_between(self, *, portfolio_id: UUID, date_from: dt.date, date_to: dt.date, profile_id: str | None = None) -> list[PortfolioSnapshot]:
        pid = resolve_profile_id(profile_id)
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")

        with new_session() as s:
            stmt = (
                select(PortfolioSnapshotRow)
                .where(PortfolioSnapshotRow.portfolio_id == str(portfolio_id))
                .where(PortfolioSnapshotRow.day >= date_from)
                .where(PortfolioSnapshotRow.day <= date_to)
                .where(PortfolioSnapshotRow.profile_id == pid)

            )
            rows = s.execute(stmt).scalars().all()
            snaps = [self._to_domain(r) for r in rows]
            snaps.sort(key=lambda s2: (s2.date, str(s2.id)))
            return snaps

    @staticmethod
    def _to_row(snap: PortfolioSnapshot, profile_id: str) -> PortfolioSnapshotRow:
        return PortfolioSnapshotRow(
            id=str(snap.id),
            portfolio_id=str(snap.portfolio_id),
            day=snap.date,
            value=Decimal(str(snap.value.amount)),
            currency=snap.value.currency.value,
            note=snap.note,
            profile_id=profile_id,
        )

    @staticmethod
    def _to_domain(r: PortfolioSnapshotRow) -> PortfolioSnapshot:
        cur = Currency(r.currency)
        value = Money(amount=r.value, currency=cur)
        return PortfolioSnapshot(
            id=UUID(r.id),
            portfolio_id=UUID(r.portfolio_id),
            date=r.day,
            value=value,
            note=r.note,
        )
