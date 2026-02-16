from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_account_repo, get_tx_repo, get_portfolio_repo, get_portfolio_snapshot_repo
from app.api.schemas.accounts import TimeSeriesPoint
from app.api.schemas.net_worth_full import NetWorthFullResponse, NetWorthFullTimeseriesResponse
from app.engine.net_worth_full import compute_net_worth_full, compute_net_worth_full_timeseries
from app.engine.account_timeseries import pick_granularity

router = APIRouter(prefix="/net-worth/full", tags=["net-worth-full"])


def _ensure_single_currency(accounts) -> str:
    currencies = {a.currency.value for a in accounts}
    if len(currencies) == 0:
        return "EUR"
    if len(currencies) > 1:
        raise HTTPException(status_code=422, detail="Multiple currencies not supported yet")
    return next(iter(currencies))


@router.get("", response_model=NetWorthFullResponse)
def get_net_worth_full(at: dt.date | None = Query(default=None)) -> NetWorthFullResponse:
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()
    p_repo = get_portfolio_repo()
    s_repo = get_portfolio_snapshot_repo()

    accounts = acc_repo.list_accounts()
    currency = _ensure_single_currency(accounts)

    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    portfolios = p_repo.list()
    snaps = s_repo.list()

    nw = compute_net_worth_full(
        accounts=accounts,
        transactions=all_txs,
        portfolios=portfolios,
        portfolio_snapshots=snaps,
        at=at,
    )

    return NetWorthFullResponse(currency=currency, at=at, net_worth_full=str(nw.amount))


@router.get("/timeseries", response_model=NetWorthFullTimeseriesResponse)
def get_net_worth_full_timeseries(
    date_from: dt.date = Query(..., alias="from"),
    date_to: dt.date = Query(..., alias="to"),
    granularity: str = Query(default="auto", pattern="^(auto|daily|weekly|monthly|yearly)$"),
) -> NetWorthFullTimeseriesResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()
    p_repo = get_portfolio_repo()
    s_repo = get_portfolio_snapshot_repo()

    accounts = acc_repo.list_accounts()
    currency = _ensure_single_currency(accounts)

    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    portfolios = p_repo.list()
    snaps = s_repo.list()

    g = pick_granularity(date_from, date_to) if granularity == "auto" else granularity

    raw = compute_net_worth_full_timeseries(
        accounts=accounts,
        transactions=all_txs,
        portfolios=portfolios,
        portfolio_snapshots=snaps,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
    )

    points = [
        TimeSeriesPoint(
            bucket=p["bucket"],
            income=str(p["income"]),
            expense=str(p["expense"]),
            net=str(p["net"]),
            balance_start=str(p["balance_start"]),
            balance_end=str(p["balance_end"]),
        )
        for p in raw
    ]

    return NetWorthFullTimeseriesResponse(
        currency=currency,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
        points=points,
    )