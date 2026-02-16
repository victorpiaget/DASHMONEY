from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from enum import Enum

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney


class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Account:
    """
    Objet métier (domain).
    Types alignés avec le repo et l'API:
    - currency: Currency
    - opening_balance: SignedMoney
    """
    id: str
    name: str
    currency: Currency
    opening_balance: SignedMoney
    opened_on: dt.date
    account_type: AccountType = AccountType.CHECKING

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("account.id must be non-empty")
        if not self.name or not self.name.strip():
            raise ValueError("account.name must be non-empty")
        if not isinstance(self.currency, Currency):
            raise ValueError("account.currency must be a Currency")
        if not isinstance(self.opening_balance, SignedMoney):
            raise ValueError("account.opening_balance must be a SignedMoney")
        if self.opening_balance.currency != self.currency:
            raise ValueError("opening_balance currency must match account currency")
        if not isinstance(self.opened_on, dt.date):
            raise ValueError("account.opened_on must be a date")