from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.domain.account import Account
from app.domain.transaction import Transaction
from app.domain.signed_money import SignedMoney
from app.engine.account_balance import compute_balance
from app.engine.account_timeseries import compute_timeseries, Granularity
from app.domain.account import AccountType


def compute_net_worth(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    at: dt.date | None,
) -> SignedMoney:
    """
    Somme des balances de tous les comptes à la date `at`.
    """

    total = Decimal("0")
    currency = None

    for account in accounts:
        account_txs = [t for t in transactions if t.account_id == account.id]

        _, _, balance, _ = compute_balance(
            opening_balance=account.opening_balance,
            transactions=account_txs,
            at=at,
        )

        total += balance.amount

        if currency is None:
            currency = balance.currency

    return SignedMoney(amount=total, currency=currency)


def compute_net_worth_timeseries(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity,
) -> list[dict]:
    """
    Agrège les timeseries de tous les comptes.
    """

    aggregated: dict[str, dict] = {}

    for account in accounts:
        account_txs = [t for t in transactions if t.account_id == account.id]

        points = compute_timeseries(
            opening_balance=account.opening_balance,
            transactions=account_txs,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )

        for p in points:
            bucket = p["bucket"]

            if bucket not in aggregated:
                aggregated[bucket] = {
                    "income": Decimal("0"),
                    "expense": Decimal("0"),
                    "net": Decimal("0"),
                    "balance_start": Decimal("0"),
                    "balance_end": Decimal("0"),
                }

            aggregated[bucket]["income"] += p["income"]
            aggregated[bucket]["expense"] += p["expense"]
            aggregated[bucket]["net"] += p["net"]
            aggregated[bucket]["balance_start"] += p["balance_start"]
            aggregated[bucket]["balance_end"] += p["balance_end"]

    # tri chronologique
    ordered = []
    for bucket in sorted(aggregated.keys()):
        ordered.append({"bucket": bucket, **aggregated[bucket]})

    return ordered


def compute_net_worth_grouped(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    at: dt.date | None,
) -> dict[str, SignedMoney]:
    """
    Retourne un mapping {AccountType -> net worth}.
    Réutilise compute_net_worth (pas de duplication).
    """
    out: dict[str, SignedMoney] = {}

    for t in AccountType:
        group_accounts = [a for a in accounts if a.account_type == t]
        if not group_accounts:
            continue

        out[t.value] = compute_net_worth(
            accounts=group_accounts,
            transactions=transactions,
            at=at,
        )

    return out


def compute_net_worth_timeseries_grouped(
    *,
    accounts: list[Account],
    transactions: list[Transaction],
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """
    Retourne:
      - total_points (list[dict])
      - groups_points (dict[type -> list[dict]])
    """
    # total
    total_points = compute_net_worth_timeseries(
        accounts=accounts,
        transactions=transactions,
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
    )

    # groups
    groups: dict[str, list[dict]] = {}
    for t in AccountType:
        group_accounts = [a for a in accounts if a.account_type == t]
        if not group_accounts:
            continue

        groups[t.value] = compute_net_worth_timeseries(
            accounts=group_accounts,
            transactions=transactions,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )

    return total_points, groups