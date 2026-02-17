from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from app.domain.price_point import PricePoint


class PriceRepository(ABC):
    @abstractmethod
    def add(self, price: PricePoint) -> None: ...

    @abstractmethod
    def list(self, *, symbol: str | None = None) -> list[PricePoint]: ...

    @abstractmethod
    def list_between(self, *, symbol: str, date_from: dt.date, date_to: dt.date) -> list[PricePoint]: ...

    @abstractmethod
    def latest(self, *, symbol: str) -> PricePoint | None: ...
