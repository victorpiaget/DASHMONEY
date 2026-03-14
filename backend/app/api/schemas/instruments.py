from pydantic import BaseModel


class InstrumentCreate(BaseModel):
    symbol: str
    kind: str
    currency: str
    name: str = ""
    ticker: str = ""


class InstrumentPatch(BaseModel):
    kind: str | None = None
    currency: str | None = None
    name: str = ""
    ticker: str = ""


class InstrumentOut(BaseModel):
    symbol: str
    kind: str
    currency: str
    name: str = ""
    ticker: str = ""
