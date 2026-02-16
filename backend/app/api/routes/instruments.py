from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import get_instrument_repo
from app.api.schemas.instruments import InstrumentCreate, InstrumentOut
from app.domain.instrument import Instrument, InstrumentKind
from app.domain.money import Currency


router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("", response_model=list[InstrumentOut])
def list_instruments():
    repo = get_instrument_repo()
    return [
        InstrumentOut(symbol=i.symbol, kind=i.kind.value, currency=i.currency.value)
        for i in repo.list()
    ]


@router.post("", response_model=InstrumentOut, status_code=201)
def create_instrument(payload: InstrumentCreate):
    repo = get_instrument_repo()

    try:
        inst = Instrument(
            symbol=payload.symbol.strip().upper(),
            kind=InstrumentKind(payload.kind.strip()),
            currency=Currency(payload.currency.strip()),
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        repo.add(inst)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return InstrumentOut(symbol=inst.symbol, kind=inst.kind.value, currency=inst.currency.value)


@router.delete("/{symbol}", status_code=204)
def delete_instrument(symbol: str):
    repo = get_instrument_repo()
    ok = repo.delete(symbol=symbol)
    if not ok:
        raise HTTPException(status_code=404, detail="instrument not found")