from __future__ import annotations

import datetime as dt
from typing import Protocol
from uuid import UUID

from app.domain.portfolio import PortfolioSnapshot


class PortfolioSnapshotRepository(Protocol):
    def add(self, snapshot: PortfolioSnapshot) -> None: ...
    def list(self, portfolio_id: UUID | None = None) -> list[PortfolioSnapshot]: ...
    def list_between(self, *, portfolio_id: UUID, date_from: dt.date, date_to: dt.date) -> list[PortfolioSnapshot]: ...