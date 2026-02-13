from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.domain.money import Currency


def _signed_tx_amount(tx: Transaction) -> SignedMoney:
    """
    Chez nous, le signe est déjà dans tx.amount.amount :
    - INCOME > 0
    - EXPENSE < 0
    - TRANSFER peut être + ou -
    """
    return tx.amount


def compute_balance(
    *,
    opening_balance: SignedMoney,
    transactions: list[Transaction],
    at: dt.date | None,
) -> tuple[SignedMoney, SignedMoney, SignedMoney, int]:
    """
    Retourne (opening_balance, tx_sum, balance, tx_count).
    Filtre les tx jusqu'à la date `at` si fournie (incluse).
    """
    txs = transactions
    if at is not None:
        txs = [t for t in txs if t.date <= at]

    # somme des tx
    total = Decimal("0")
    for t in txs:
        total += _signed_tx_amount(t).amount

    tx_sum = SignedMoney(amount=total, currency=opening_balance.currency)
    balance = SignedMoney(amount=opening_balance.amount + tx_sum.amount, currency=opening_balance.currency)

    return opening_balance, tx_sum, balance, len(txs)