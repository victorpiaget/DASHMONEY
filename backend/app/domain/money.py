from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"

_QUANT = Decimal("0.01")


def _parse_decimal(value: str) -> Decimal:
    """
    Parse robuste depuis string.
    Autorise "12.34", "-12.34", "12", et optionnellement "12,34".
    """
    if not isinstance(value, str):
        raise TypeError("Amount must be provided as a string")

    raw = value.strip()
    if raw == "":
        raise ValueError("Amount cannot be empty")

    # tolérance minimale pour les virgules françaises
    raw = raw.replace(",", ".")

    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal amount: {value!r}") from exc


def _quantize_money(amount: Decimal) -> Decimal:
    # Arrondi comptable classique
    return amount.quantize(_QUANT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    """
    Money = quantité d'argent non négative (stock / valeur).
    Ex: valeur d'un actif, capital restant dû, etc.
    """
    amount: Decimal
    currency: Currency

    @classmethod
    def from_str(cls, amount: str, currency: Currency) -> "Money":
        dec = _quantize_money(_parse_decimal(amount))
        return cls(amount=dec, currency=currency)

    def __post_init__(self) -> None:
        if not isinstance(self.currency, Currency):
            raise ValueError("Invalid currency")

        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal")

        # normalisation même si créé autrement que from_str
        q = _quantize_money(self.amount)
        object.__setattr__(self, "amount", q)

        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

    def is_zero(self) -> bool:
        return self.amount == Decimal("0.00")