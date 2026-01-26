from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction


@dataclass(frozen=True)
class TransactionWithBalance:
    transaction: Transaction
    balance_after: SignedMoney


def _sorted_transactions(transactions: Iterable[Transaction]) -> list[Transaction]:
    return sorted(transactions, key=lambda t: (t.date, t.sequence))


def compute_running_balance_strict(
    transactions: list[Transaction],
    *,
    opening_balance: SignedMoney,
) -> list[TransactionWithBalance]:
    if not transactions:
        return []

    txs = _sorted_transactions(transactions)

    expected_account_id = txs[0].account_id
    expected_currency = txs[0].amount.currency

    # opening balance doit matcher la devise des tx
    if opening_balance.currency != expected_currency:
        raise ValueError("opening_balance currency mismatch")

    for t in txs:
        if t.account_id != expected_account_id:
            raise ValueError("mixed account_id in compute_running_balance_strict")
        if t.amount.currency != expected_currency:
            raise ValueError("mixed currency in compute_running_balance_strict")

    balance = opening_balance
    out: list[TransactionWithBalance] = []
    for t in txs:
        balance = balance + t.amount
        out.append(TransactionWithBalance(transaction=t, balance_after=balance))

    return out
