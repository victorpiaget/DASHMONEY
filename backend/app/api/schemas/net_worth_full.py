from pydantic import BaseModel
import datetime as dt
from app.api.schemas.accounts import TimeSeriesPoint


class NetWorthFullResponse(BaseModel):
    currency: str
    at: dt.date | None
    net_worth_full: str


class NetWorthFullTimeseriesResponse(BaseModel):
    currency: str
    date_from: dt.date
    date_to: dt.date
    granularity: str
    points: list[TimeSeriesPoint]