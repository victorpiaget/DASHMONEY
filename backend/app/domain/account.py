from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import datetime as dt
from enum import Enum

class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    OTHER = "OTHER"



@dataclass(frozen=True, slots=True)
class Account:
    """
    Objet métier (domain).
    - Aucun import FastAPI/Pydantic/JSON ici.
    - Types stricts et stables pour faciliter les calculs et tests.
    """
    id: str
    name: str
    currency: str  # MVP: "EUR", "USD", etc.
    opening_balance: Decimal
    opened_on: dt.date
    account_type: AccountType = AccountType.CHECKING

    def __post_init__(self) -> None:
        # Petites validations "métier" minimales (MVP)
        if not self.id or not self.id.strip():
            raise ValueError("account.id must be non-empty")
        if not self.name or not self.name.strip():
            raise ValueError("account.name must be non-empty")
        if not self.currency or not self.currency.strip():
            raise ValueError("account.currency must be non-empty")
        
