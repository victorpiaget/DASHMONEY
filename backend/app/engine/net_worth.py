from dataclasses import dataclass
from typing import Iterable, Dict
from decimal import Decimal

from app.domain.money import Money, Currency
from app.domain.asset import Asset
from app.domain.liability import Liability

# ⚠️ Si tu déplaces SignedMoney dans domain (recommandé)
from app.domain.signed_money import SignedMoney
# sinon, si tu le laisses temporairement en engine :
# from app.engine.signed_money import SignedMoney


@dataclass(frozen=True)
class NetWorthResult:
    assets_total: Dict[Currency, Money]
    liabilities_total: Dict[Currency, Money]
    net_total: Dict[Currency, SignedMoney]


def compute_net_worth(
    assets: Iterable[Asset],
    liabilities: Iterable[Liability],
) -> NetWorthResult:
    """
    Calcule la valeur nette à partir d'actifs et de dettes.

    Règles :
    - Aucune conversion de devise
    - Calcul séparé par devise
    - Fonction pure : mêmes entrées → mêmes sorties
    """

    # ✅ Decimal partout
    assets_sum: Dict[Currency, Decimal] = {}
    liabilities_sum: Dict[Currency, Decimal] = {}

    # 1️⃣ Agrégation des actifs
    for asset in assets:
        currency = asset.value.currency
        if currency not in assets_sum:
            assets_sum[currency] = Decimal("0.00")

        # asset.value.amount doit être Decimal maintenant
        assets_sum[currency] += asset.value.amount

    # 2️⃣ Agrégation des dettes
    for liability in liabilities:
        currency = liability.balance.currency
        if currency not in liabilities_sum:
            liabilities_sum[currency] = Decimal("0.00")

        liabilities_sum[currency] += liability.balance.amount

    # 3️⃣ Construction des résultats finaux
    assets_total: Dict[Currency, Money] = {}
    liabilities_total: Dict[Currency, Money] = {}
    net_total: Dict[Currency, SignedMoney] = {}

    all_currencies = set(assets_sum.keys()) | set(liabilities_sum.keys())

    for currency in all_currencies:
        total_assets = assets_sum.get(currency, Decimal("0.00"))
        total_liabilities = liabilities_sum.get(currency, Decimal("0.00"))

        # Money normalise/quantize dans __post_init__
        assets_total[currency] = Money(amount=total_assets, currency=currency)
        liabilities_total[currency] = Money(amount=total_liabilities, currency=currency)

        net_amount = total_assets - total_liabilities
        net_total[currency] = SignedMoney(amount=net_amount, currency=currency)

    return NetWorthResult(
        assets_total=assets_total,
        liabilities_total=liabilities_total,
        net_total=net_total,
    )
