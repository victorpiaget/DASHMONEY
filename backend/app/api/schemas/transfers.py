from datetime import date
from pydantic import BaseModel, Field
from uuid import UUID
from app.api.schemas.transactions import TransactionResponse


class TransferCreateRequest(BaseModel):
    to_account_id: str = Field(..., min_length=1)
    date: date
    amount: str = Field(
        ...,
        pattern=r"^\d+(\.\d{1,2})?$",
        description="Positive amount as string, e.g. '500.00'",
        examples=["500.00"],
    )
    category: str = Field(..., min_length=1)
    subcategory: str | None = None
    label: str | None = None


class TransferResponse(BaseModel):
    transfer_id: UUID
    from_transaction: TransactionResponse
    to_transaction: TransactionResponse