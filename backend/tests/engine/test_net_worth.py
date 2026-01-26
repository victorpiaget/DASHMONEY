from app.domain.asset import Asset, AssetCategory
from app.domain.liability import Liability
from app.domain.money import Money, Currency
from app.engine.net_worth import compute_net_worth


def test_net_worth_single_currency():
    # Actifs en EUR
    assets = [
        Asset.create(
            name="Compte courant",
            category=AssetCategory.FINANCIAL,
            value=Money.from_str("5_000.0", Currency.EUR),
        ),
        Asset.create(
            name="Livret A",
            category=AssetCategory.FINANCIAL,
            value=Money.from_str("10_000.0", Currency.EUR),
        ),
    ]

    # Dettes en EUR
    liabilities = [
        Liability.create(
            name="Crédit auto",
            balance=Money.from_str("3_000.0", Currency.EUR),
        )
    ]

    result = compute_net_worth(assets, liabilities)

    # Vérification des totaux
    assert result.assets_total[Currency.EUR].amount == 15_000.0
    assert result.liabilities_total[Currency.EUR].amount == 3_000.0
    assert result.net_total[Currency.EUR].amount == 12_000.0


def test_net_worth_multi_currency():
    assets = [
        Asset.create(
            name="Compte EUR",
            category=AssetCategory.FINANCIAL,
            value=Money.from_str("10_000.0", Currency.EUR),
        ),
        Asset.create(
            name="Compte USD",
            category=AssetCategory.FINANCIAL,
            value=Money.from_str("2_000.0", currency=Currency.USD),
        ),
    ]

    liabilities = [
        Liability.create(
            name="Dette USD",
            balance=Money.from_str("3_000.0", currency=Currency.USD),
        )
    ]

    result = compute_net_worth(assets, liabilities)

    # EUR : pas de dette
    assert result.net_total[Currency.EUR].amount == 10_000.0

    # USD : dette > actif → net négatif
    assert result.net_total[Currency.USD].amount == -1_000.0
