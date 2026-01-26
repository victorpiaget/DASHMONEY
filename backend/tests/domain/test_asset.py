import pytest

# On importe le modèle métier Asset et ses catégories
from app.domain.asset import Asset, AssetCategory

# On importe Money et Currency (déjà faits)
from app.domain.money import Money, Currency


def test_asset_create_ok():
    # valeur 0 autorisée (tu l'as validé)
    value = Money.from_str("0.0", Currency.EUR)

    # création via la factory -> génère un UUID automatiquement
    a = Asset.create(
        name="Compte courant",
        category=AssetCategory.FINANCIAL,
        value=value,
    )

    # On vérifie que les champs sont bien stockés
    assert a.name == "Compte courant"
    assert a.category == AssetCategory.FINANCIAL
    assert a.value == value

    # On vérifie que l'id existe (UUID généré)
    assert a.id is not None


def test_asset_name_cannot_be_empty():
    value = Money.from_str("10.0", Currency.EUR)

    # name = "   " => seulement des espaces => doit lever une erreur
    with pytest.raises(ValueError):
        Asset.create(name="   ", category=AssetCategory.FINANCIAL, value=value)


def test_asset_category_must_be_enum():
    value = Money.from_str("10.0", Currency.EUR)

    # Ici on simule une mauvaise utilisation : category passé en string
    # Asset doit refuser car on veut un Enum (sinon risque de catégories incohérentes)
    with pytest.raises(ValueError):
        Asset.create(name="Livret A", category="FINANCIAL", value=value)  # type: ignore


def test_asset_value_must_be_money():
    # Mauvaise utilisation : value passé en float au lieu de Money
    # On veut forcer l'utilisation de Money partout dans le domaine
    with pytest.raises(ValueError):
        Asset.create(name="Livret A", category=AssetCategory.FINANCIAL, value=100.0)  # type: ignore
