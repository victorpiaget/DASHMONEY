from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_account_repo, get_tx_repo
from app.api.schemas.net_worth import NetWorthResponse, NetWorthTimeseriesResponse,NetWorthGroupedResponse,NetWorthGroupLine,NetWorthTimeseriesGroupedResponse, NetWorthTimeseriesGroup
from app.api.schemas.accounts import TimeSeriesPoint

from app.engine.net_worth import compute_net_worth, compute_net_worth_timeseries, compute_net_worth_grouped,compute_net_worth_timeseries_grouped
from app.engine.account_timeseries import pick_granularity

from app.domain.account import AccountType

router = APIRouter(prefix="/net-worth", tags=["net-worth"])


def _ensure_single_currency(accounts) -> str:
    currencies = {a.currency.value for a in accounts}  # Currency enum
    if len(currencies) == 0:
        return "EUR"  # fallback MVP si aucun compte
    if len(currencies) > 1:
        raise HTTPException(status_code=422, detail="Multiple currencies not supported yet")
    return next(iter(currencies))

def _parse_types(types: str | None) -> set[AccountType] | None:
    """
    types = "CHECKING,SAVINGS" -> {AccountType.CHECKING, AccountType.SAVINGS}
    None -> None (pas de filtre)
    """
    if types is None or not types.strip():
        return None

    raw = [x.strip() for x in types.split(",") if x.strip()]
    if not raw:
        return None

    out: set[AccountType] = set()
    for s in raw:
        try:
            out.add(AccountType(s))
        except Exception:
            raise HTTPException(status_code=422, detail=f"Invalid account_type '{s}'")
    return out


def _filter_accounts_by_type(accounts, selected: set[AccountType] | None):
    if selected is None:
        return accounts
    return [a for a in accounts if a.account_type in selected]

@router.get("", response_model=NetWorthResponse)
def get_net_worth(
    at: dt.date | None = Query(default=None),
    types: str | None = Query(default=None, description="CSV of account types, e.g. CHECKING,SAVINGS"),
) -> NetWorthResponse:
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    accounts = acc_repo.list_accounts()
    selected = _parse_types(types)
    accounts = _filter_accounts_by_type(accounts, selected)
    currency = _ensure_single_currency(accounts)

    # On récupère toutes les transactions (par compte) puis on agrège via le moteur
    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    nw = compute_net_worth(
        accounts=accounts,
        transactions=all_txs,
        at=at,
    )

    return NetWorthResponse(
        currency=currency,
        at=at,
        net_worth=str(nw.amount),
    )


@router.get("/timeseries", response_model=NetWorthTimeseriesResponse)
def get_net_worth_timeseries(
    date_from: dt.date = Query(..., alias="from"),
    date_to: dt.date = Query(..., alias="to"),
    granularity: str = Query(default="auto", pattern="^(auto|daily|weekly|monthly|yearly)$"),
    types: str | None = Query(default=None, description="CSV of account types, e.g. CHECKING,SAVINGS"),
) -> NetWorthTimeseriesResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    accounts = acc_repo.list_accounts()
    selected = _parse_types(types)
    accounts = _filter_accounts_by_type(accounts, selected)
    currency = _ensure_single_currency(accounts)

    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    g = pick_granularity(date_from, date_to) if granularity == "auto" else granularity

    raw = compute_net_worth_timeseries(
        accounts=accounts,
        transactions=all_txs,
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

    return NetWorthTimeseriesResponse(
        currency=currency,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
        points=points,
    )

@router.get("/grouped", response_model=NetWorthGroupedResponse)
def get_net_worth_grouped(
    at: dt.date | None = Query(default=None),
    types: str | None = Query(default=None, description="CSV of account types, e.g. CHECKING,SAVINGS"),
) -> NetWorthGroupedResponse:
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    accounts = acc_repo.list_accounts()
    selected = _parse_types(types)
    accounts = _filter_accounts_by_type(accounts, selected)
    currency = _ensure_single_currency(accounts)

    # On récupère toutes les transactions (par compte) puis on agrège via le moteur
    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    total = compute_net_worth(accounts=accounts, transactions=all_txs, at=at)
    groups = compute_net_worth_grouped(accounts=accounts, transactions=all_txs, at=at)

    return NetWorthGroupedResponse(
        currency=currency,
        at=at,
        total=str(total.amount),
        groups=[
            NetWorthGroupLine(key=k, net_worth=str(v.amount))
            for k, v in sorted(groups.items())
        ],
    )


@router.get("/timeseries/grouped", response_model=NetWorthTimeseriesGroupedResponse)
def get_net_worth_timeseries_grouped(
    date_from: dt.date = Query(..., alias="from"),
    date_to: dt.date = Query(..., alias="to"),
    granularity: str = Query(default="auto", pattern="^(auto|daily|weekly|monthly|yearly)$"),
    types: str | None = Query(default=None, description="CSV of account types, e.g. CHECKING,SAVINGS"),
) -> NetWorthTimeseriesGroupedResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    accounts = acc_repo.list_accounts()
    selected = _parse_types(types)
    accounts = _filter_accounts_by_type(accounts, selected)

    currency = _ensure_single_currency(accounts)

    all_txs = []
    for acc in accounts:
        all_txs.extend(tx_repo.list(account_id=acc.id))

    g = pick_granularity(date_from, date_to) if granularity == "auto" else granularity

    total_raw, groups_raw = compute_net_worth_timeseries_grouped(
        accounts=accounts,
        transactions=all_txs,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
    )

    def to_points(raw: list[dict]) -> list[TimeSeriesPoint]:
        return [
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

    groups = [
        NetWorthTimeseriesGroup(key=k, points=to_points(v))
        for k, v in sorted(groups_raw.items())
    ]

    return NetWorthTimeseriesGroupedResponse(
        currency=currency,
        date_from=date_from,
        date_to=date_to,
        granularity=g,
        total_points=to_points(total_raw),
        groups=groups,
    )