from pydantic import BaseModel
import datetime as dt
from uuid import UUID
from typing import Optional


class PortfolioCreate(BaseModel):
    name: str
    currency: str
    portfolio_type: str
    opened_on: dt.date


class PortfolioOut(BaseModel):
    id: UUID
    name: str
    currency: str
    portfolio_type: str
    opened_on: dt.date
    cash_account_id: str


class PortfolioSnapshotCreate(BaseModel):
    date: dt.date
    value: str
    currency: str
    note: Optional[str] = None


class PortfolioSnapshotOut(BaseModel):
    id: UUID
    portfolio_id: UUID
    date: dt.date
    value: str
    currency: str
    note: Optional[str] = None

class PortfolioUpdateRequest(BaseModel):
    name: Optional[str] = None
    portfolio_type: Optional[str] = None