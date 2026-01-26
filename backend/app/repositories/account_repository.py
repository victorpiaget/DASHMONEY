from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.domain.money import Currency
from app.domain.signed_money import SignedMoney


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    currency: Currency
    opening_balance: SignedMoney
    opened_on: date


class AccountRepository(Protocol):
    def list_accounts(self) -> list[Account]: ...
    def get_account(self, account_id: str) -> Account: ...
