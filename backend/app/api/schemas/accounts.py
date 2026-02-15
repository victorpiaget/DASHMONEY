from pydantic import BaseModel, Field
import datetime as dt

class AccountCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    currency: str = Field(min_length=1)          # "EUR"
    opening_balance: str = Field(min_length=1)   # "0.00 EUR" ou format attendu par SignedMoney
    opened_on: dt.date
    account_type: str = "CHECKING"


class AccountResponse(BaseModel):
    id: str
    name: str
    currency: str
    opening_balance: str
    opened_on: dt.date
    account_type: str
    

class AccountBalanceResponse(BaseModel):
    account_id: str
    currency: str
    at: dt.date | None
    opening_balance: str
    transactions_sum: str
    balance: str
    transactions_count: int


class TimeSeriesPoint(BaseModel):
    bucket: str
    income: str
    expense: str
    net: str
    balance_start: str 
    balance_end: str

class AccountTimeSeriesResponse(BaseModel):
    account_id: str
    currency: str
    date_from: dt.date
    date_to: dt.date
    granularity: str
    points: list[TimeSeriesPoint]