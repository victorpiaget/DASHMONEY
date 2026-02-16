from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID

from app.api.deps import get_portfolio_repo, get_portfolio_snapshot_repo,get_account_repo
from app.api.schemas.portfolios import (
    PortfolioCreate, PortfolioOut,
    PortfolioSnapshotCreate, PortfolioSnapshotOut
)
from app.domain.money import Currency, Money
from app.domain.portfolio import Portfolio, PortfolioSnapshot, PortfolioType

from app.domain.account import Account, AccountType

from app.domain.signed_money import SignedMoney
from decimal import Decimal

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioOut])
def list_portfolios():
    repo = get_portfolio_repo()
    out = []
    for p in repo.list():
        out.append(PortfolioOut(
            id=p.id,
            name=p.name,
            currency=p.currency.value,
            portfolio_type=p.portfolio_type.value,
            opened_on=p.opened_on,
            cash_account_id=p.cash_account_id,
        ))
    return out


@router.post("", response_model=PortfolioOut)
def create_portfolio(payload: PortfolioCreate):
    repo = get_portfolio_repo()

    try:
        p = Portfolio.create(
            name=payload.name,
            currency=Currency(payload.currency),
            portfolio_type=PortfolioType(payload.portfolio_type),
            opened_on=payload.opened_on,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


    def create_account_if_missing(*, account_id: str, name: str, currency, opened_on: dt.date) -> None:
        """
        Crée un compte passerelle si absent.
        Compatible avec ton domain Account (dataclass) et ton JsonAccountRepository.add().
        """
        repo = get_account_repo()

        try:
            repo.get_account(account_id)
            return
        except KeyError:
            pass

        # opening_balance must be SignedMoney, opened_on is required
        opening_balance = SignedMoney(amount=Decimal("0.00"), currency=currency)

        try:
            account = Account(
                id=account_id.strip(),
                name=name.strip(),
                currency=currency,
                opening_balance=opening_balance,
                opened_on=opened_on,
                account_type=AccountType.OTHER,
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"cannot create pass-through account: {e}")

        try:
            repo.add(account)  # <-- c'est bien add() dans ton repo :contentReference[oaicite:3]{index=3}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to persist pass-through account: {e}")


    repo.add(p)

    
    create_account_if_missing(
        account_id=p.cash_account_id,
        name=f"Passerelle - {p.name}",
        currency=p.currency,
        opened_on=p.opened_on,
    )

    return PortfolioOut(
        id=p.id,
        name=p.name,
        currency=p.currency.value,
        portfolio_type=p.portfolio_type.value,
        opened_on=p.opened_on,
        cash_account_id=p.cash_account_id,
    )


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: UUID):
    repo = get_portfolio_repo()
    ok = repo.delete(portfolio_id=portfolio_id)
    if not ok:
        raise HTTPException(status_code=404, detail="portfolio not found")
    return {"deleted": True}


@router.post("/{portfolio_id}/snapshots", response_model=PortfolioSnapshotOut)
def add_snapshot(portfolio_id: UUID, payload: PortfolioSnapshotCreate):
    p_repo = get_portfolio_repo()
    s_repo = get_portfolio_snapshot_repo()

    try:
        portfolio = p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    try:
        cur = Currency(payload.currency)
        value = Money.from_str(payload.value, cur)
        if cur != portfolio.currency:
            raise HTTPException(status_code=422, detail="snapshot currency must match portfolio currency")
        snap = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            date=payload.date,
            value=value,
            note=payload.note,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    s_repo.add(snap)
    return PortfolioSnapshotOut(
        id=snap.id,
        portfolio_id=snap.portfolio_id,
        date=snap.date,
        value=f"{snap.value.amount:.2f}",
        currency=snap.value.currency.value,
        note=snap.note,
    )


@router.get("/{portfolio_id}/snapshots", response_model=list[PortfolioSnapshotOut])
def list_snapshots(
    portfolio_id: UUID,
    date_from: dt.date | None = Query(default=None, alias="from"),
    date_to: dt.date | None = Query(default=None, alias="to"),
):
    p_repo = get_portfolio_repo()
    s_repo = get_portfolio_snapshot_repo()

    try:
        p_repo.get(portfolio_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    snaps = s_repo.list(portfolio_id=portfolio_id)
    if date_from is not None:
        snaps = [s for s in snaps if s.date >= date_from]
    if date_to is not None:
        snaps = [s for s in snaps if s.date <= date_to]

    return [
        PortfolioSnapshotOut(
            id=s.id,
            portfolio_id=s.portfolio_id,
            date=s.date,
            value=f"{s.value.amount:.2f}",
            currency=s.value.currency.value,
            note=s.note,
        )
        for s in snaps
    ]