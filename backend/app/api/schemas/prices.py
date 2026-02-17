from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field


class PriceOut(BaseModel):
    symbol: str
    day: dt.date
    price: str
    currency: str
    source: str
    captured_at: dt.datetime


class PriceUpdateResult(BaseModel):
    day: dt.date
    stored: int = Field(ge=0)
    skipped: int = Field(ge=0)
