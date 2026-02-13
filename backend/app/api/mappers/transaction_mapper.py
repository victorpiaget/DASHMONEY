from __future__ import annotations

from app.api.schemas.transactions import TransactionResponse
from app.domain.transaction import Transaction


def tx_to_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(tx.id),
        account_id=tx.account_id,
        date=tx.date,
        sequence=tx.sequence,
        amount=str(tx.amount.amount),
        currency=tx.amount.currency.value,  # si ton schema attend une string
        kind=tx.kind,
        category=tx.category,
        subcategory=tx.subcategory,
        label=tx.label,
        created_at=tx.created_at,
        transfer_id=str(tx.transfer_id) if tx.transfer_id else None,  # si tu l'as ajouté au schema
    )