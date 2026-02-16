from pydantic import BaseModel
import datetime as dt
from uuid import UUID
from typing import Optional


class TradeCreate(BaseModel):
    date: dt.date
    side: str
    instrument_symbol: str
    quantity: str
    price: str
    fees: str = "0"
    label: Optional[str] = None


class TradePatch(BaseModel):
    date: Optional[dt.date] = None
    side: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    fees: Optional[str] = None
    label: Optional[str] = None


class TradeOut(BaseModel):
    id: UUID
    portfolio_id: UUID
    date: dt.date
    side: str
    instrument_symbol: str
    quantity: str
    price: str
    fees: str
    currency: str
    label: Optional[str]
    linked_cash_tx_id: Optional[UUID]


class PositionOut(BaseModel):
    instrument_symbol: str
    quantity: str