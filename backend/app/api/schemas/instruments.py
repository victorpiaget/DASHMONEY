from pydantic import BaseModel


class InstrumentCreate(BaseModel):
    symbol: str
    kind: str
    currency: str


class InstrumentOut(BaseModel):
    symbol: str
    kind: str
    currency: str