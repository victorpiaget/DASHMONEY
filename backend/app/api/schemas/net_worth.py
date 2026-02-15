from pydantic import BaseModel
import datetime as dt

from app.api.schemas.accounts import TimeSeriesPoint  # on réutilise exactement ton point existant


class NetWorthResponse(BaseModel):
    currency: str
    at: dt.date | None
    net_worth: str


class NetWorthTimeseriesResponse(BaseModel):
    currency: str
    date_from: dt.date
    date_to: dt.date
    granularity: str
    points: list[TimeSeriesPoint]

class NetWorthGroupLine(BaseModel):
    key: str          # ex: "SAVINGS"
    net_worth: str    # Decimal en string


class NetWorthGroupedResponse(BaseModel):
    currency: str
    at: dt.date | None
    total: str
    groups: list[NetWorthGroupLine]