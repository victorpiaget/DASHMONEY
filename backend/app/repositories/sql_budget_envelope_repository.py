from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey, select, delete
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.budget_envelope import BudgetEnvelope
from app.domain.money import Currency, Money
from app.domain.transaction import TransactionKind
from app.identity.profile_scope import resolve_profile_id
from app.repositories.sql_identity_models import ProfileRow  # noqa: F401


class BudgetEnvelopeRow(Base):
    __tablename__ = "budget_envelopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)


def _row_to_domain(row: BudgetEnvelopeRow) -> BudgetEnvelope:
    return BudgetEnvelope(
        id=UUID(row.id),
        category=row.category,
        subcategory=row.subcategory,
        kind=TransactionKind(row.kind),
        amount=Money(amount=row.amount, currency=Currency(row.currency)),
    )


class SqlBudgetEnvelopeRepository:

    def __init__(self) -> None:
        init_db()

    def list(self, *, profile_id: str | None = None) -> list[BudgetEnvelope]:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            rows = s.execute(
                select(BudgetEnvelopeRow)
                .where(BudgetEnvelopeRow.profile_id == pid)
                .order_by(BudgetEnvelopeRow.kind, BudgetEnvelopeRow.category, BudgetEnvelopeRow.subcategory)
            ).scalars().all()
            return [_row_to_domain(r) for r in rows]

    def upsert(self, envelope: BudgetEnvelope, *, profile_id: str | None = None) -> BudgetEnvelope:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            # Check if row already exists for (profile_id, category, subcategory, kind)
            existing = s.execute(
                select(BudgetEnvelopeRow).where(
                    BudgetEnvelopeRow.profile_id == pid,
                    BudgetEnvelopeRow.category == envelope.category,
                    BudgetEnvelopeRow.kind == envelope.kind.value,
                    BudgetEnvelopeRow.subcategory == envelope.subcategory
                    if envelope.subcategory is not None
                    else BudgetEnvelopeRow.subcategory.is_(None),
                )
            ).scalar_one_or_none()

            if existing is not None:
                existing.amount = envelope.amount.amount
                existing.currency = envelope.amount.currency.value
                s.commit()
                return _row_to_domain(existing)

            row = BudgetEnvelopeRow(
                id=str(envelope.id),
                profile_id=pid,
                category=envelope.category,
                subcategory=envelope.subcategory,
                kind=envelope.kind.value,
                amount=envelope.amount.amount,
                currency=envelope.amount.currency.value,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _row_to_domain(row)

    def delete(self, envelope_id: str, *, profile_id: str | None = None) -> bool:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            row = s.execute(
                select(BudgetEnvelopeRow).where(
                    BudgetEnvelopeRow.id == envelope_id,
                    BudgetEnvelopeRow.profile_id == pid,
                )
            ).scalar_one_or_none()
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def delete_by_category(
        self,
        category: str,
        subcategory: str | None = None,
        kind: TransactionKind | None = None,
        *,
        profile_id: str | None = None,
    ) -> int:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            stmt = select(BudgetEnvelopeRow).where(
                BudgetEnvelopeRow.profile_id == pid,
                BudgetEnvelopeRow.category == category,
            )
            if subcategory is not None:
                stmt = stmt.where(BudgetEnvelopeRow.subcategory == subcategory)
            if kind is not None:
                stmt = stmt.where(BudgetEnvelopeRow.kind == kind.value)

            rows = s.execute(stmt).scalars().all()
            count = len(rows)
            for row in rows:
                s.delete(row)
            s.commit()
            return count
