from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.domain.account import Account
from app.domain.transaction import Transaction
from app.domain.money import Currency
from app.domain.portfolio import Portfolio, PortfolioSnapshot
from app.domain.signed_money import SignedMoney
from app.engine.net_worth import compute_net_worth, compute_net_worth_timeseries
from app.engine.portfolio_value import compute_portfolios_value, bucket_end_date


def compute_net_worth_full(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    portfolios: list[Portfolio],
    portfolio_snapshots: list[PortfolioSnapshot],
    at: dt.date | None,
) -> SignedMoney:
    cash = compute_net_worth(accounts=accounts, transactions=transactions, at=at)

    currency = cash.currency
    if currency is None:
        # cas "aucun compte" => on ne supporte pas vraiment, mais on fallback EUR
        currency = Currency.EUR

    portfolios_value = compute_portfolios_value(
        portfolios=portfolios,
        snapshots=portfolio_snapshots,
        at=at,
        currency=currency,
    )

    return SignedMoney(amount=cash.amount + portfolios_value.amount, currency=currency)


def compute_net_worth_full_timeseries(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    portfolios: list[Portfolio],
    portfolio_snapshots: list[PortfolioSnapshot],
    date_from: dt.date,
    date_to: dt.date,
    granularity: str,
) -> list[dict]:
    """
    On réutilise ta timeseries cash (income/expense/net/balance_start/end),
    puis on ajoute la valeur des portfolios dans balance_start/end.
    """
    cash_points = compute_net_worth_timeseries(
        accounts=accounts,
        transactions=transactions,
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
    )

    # currency fix: on prend celle du cash (même convention que ton API)
    currency = None
    for a in accounts:
        currency = a.currency
        break
    currency = currency or Currency.EUR

    out: list[dict] = []
    for p in cash_points:
        as_of = bucket_end_date(p["bucket"], granularity, date_from, date_to)

        pv = compute_portfolios_value(
            portfolios=portfolios,
            snapshots=portfolio_snapshots,
            at=as_of,
            currency=currency,
        )

        out.append(
            {
                **p,
                "balance_start": p["balance_start"] + pv.amount,
                "balance_end": p["balance_end"] + pv.amount,
            }
        )

    return out