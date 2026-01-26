# FastAPI router = ensemble de routes regroupées
from fastapi import APIRouter

# On importe les schemas API (input/output)
from app.api.schemas.net_worth import (
    NetWorthComputeRequest,
    NetWorthComputeResponse,
    MoneyOut,
    SignedMoneyOut,
)

# On importe les objets domain + enums
from app.domain.money import Money, Currency
from app.domain.asset import Asset, AssetCategory
from app.domain.liability import Liability

# On importe le calcul engine
from app.engine.net_worth import compute_net_worth

router = APIRouter(prefix="/net-worth", tags=["net-worth"])


def _parse_asset_category(raw: str) -> AssetCategory:
    """
    Convertit une string reçue par l'API en AssetCategory.
    On accepte plusieurs écritures pour éviter de bloquer le frontend.
    """
    s = raw.strip().upper()

    # On mappe des alias simples
    if s in {"FINANCIER", "FINANCIAL"}:
        return AssetCategory.FINANCIAL
    if s in {"IMMO", "IMMOBILIER", "REAL_ESTATE", "REALESTATE"}:
        return AssetCategory.REAL_ESTATE
    if s in {"PHYSIQUE", "PHYSICAL"}:
        return AssetCategory.PHYSICAL

    # Si c'est inconnu, on lève une erreur claire
    raise ValueError(f"Unknown asset category: {raw}")


@router.post("/compute", response_model=NetWorthComputeResponse)
def compute_net_worth_endpoint(payload: NetWorthComputeRequest) -> NetWorthComputeResponse:
    """
    Endpoint HTTP:
    - reçoit assets/liabilities en JSON
    - convertit vers domain
    - appelle engine.compute_net_worth
    - renvoie un résultat JSON structuré
    """

    # 1) Convertir les assets "API" -> assets "domain"
    domain_assets: list[Asset] = []
    for a in payload.assets:
        category = _parse_asset_category(a.category)

        # Money du domain vérifie >= 0 + devise valide
        value = Money(amount=a.value.amount, currency=a.value.currency)

        domain_assets.append(Asset.create(name=a.name, category=category, value=value))

    # 2) Convertir les liabilities "API" -> liabilities "domain"
    domain_liabilities: list[Liability] = []
    for l in payload.liabilities:
        balance = Money(amount=l.balance.amount, currency=l.balance.currency)
        domain_liabilities.append(Liability.create(name=l.name, balance=balance))

    # 3) Appeler le moteur de calcul (engine)
    result = compute_net_worth(domain_assets, domain_liabilities)

    # 4) Convertir le résultat engine -> réponse API
    # Note : result.assets_total est dict[Currency, Money]
    assets_total_out = {
        c: MoneyOut(amount=m.amount, currency=m.currency)
        for c, m in result.assets_total.items()
    }
    liabilities_total_out = {
        c: MoneyOut(amount=m.amount, currency=m.currency)
        for c, m in result.liabilities_total.items()
    }
    net_total_out = {
        c: SignedMoneyOut(amount=sm.amount, currency=sm.currency)
        for c, sm in result.net_total.items()
    }

    return NetWorthComputeResponse(
        assets_total=assets_total_out,
        liabilities_total=liabilities_total_out,
        net_total=net_total_out,
    )
