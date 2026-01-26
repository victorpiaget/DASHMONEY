import pytest

# Import de la classe métier Liability
from app.domain.liability import Liability

# Import de Money et Currency
from app.domain.money import Money, Currency


def test_liability_create_ok():
    # Montant dû : 100 000 €
    balance = Money.from_str("100_000.0", Currency.EUR)

    # Création via la factory
    liability = Liability.create(
        name="Crédit immobilier",
        balance=balance,
    )

    # Vérifications basiques
    assert liability.name == "Crédit immobilier"
    assert liability.balance == balance
    assert liability.id is not None


def test_liability_name_cannot_be_empty():
    balance = Money.from_str("10_000.0", Currency.EUR)

    # Nom vide => erreur
    with pytest.raises(ValueError):
        Liability.create(name="   ", balance=balance)


def test_liability_balance_must_be_money():
    # Balance passée en float au lieu de Money => erreur
    with pytest.raises(ValueError):
        Liability.create(name="Prêt étudiant", balance=5_000.0)  # type: ignore
