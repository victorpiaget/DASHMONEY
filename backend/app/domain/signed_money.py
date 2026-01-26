from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import Currency, _parse_decimal, _quantize_money


@dataclass(frozen=True)
class SignedMoney:
    amount: Decimal
    currency: Currency

    @classmethod
    def from_str(cls, amount: str, currency: Currency) -> "SignedMoney":
        dec = _quantize_money(_parse_decimal(amount))
        return cls(amount=dec, currency=currency)

    @classmethod
    def zero(cls, currency: Currency) -> "SignedMoney":
        return cls(amount=Decimal("0.00"), currency=currency)

    def __post_init__(self) -> None:
        if not isinstance(self.currency, Currency):
            raise ValueError("Invalid currency")

        if not isinstance(self.amount, Decimal):
            raise TypeError("SignedMoney.amount must be a Decimal")

        q = _quantize_money(self.amount)
        object.__setattr__(self, "amount", q)

    def is_positive(self) -> bool:
        return self.amount >= Decimal("0.00")

    def is_negative(self) -> bool:
        return self.amount < Decimal("0.00")

    def __add__(self, other: "SignedMoney") -> "SignedMoney":
        if not isinstance(other, SignedMoney):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot add SignedMoney with different currency")
        return SignedMoney(amount=self.amount + other.amount, currency=self.currency)



