from fastapi import APIRouter
from decimal import Decimal

from app.api.schemas.net_worth import (
    NetWorthComputeRequest,
    NetWorthComputeResponse,
    MoneyOut,
    SignedMoneyOut,
)

from app.domain.money import Money
from app.domain.asset import Asset, AssetCategory
from app.domain.liability import Liability

from app.engine.net_worth import compute_net_worth

router = APIRouter(prefix="/net-worth", tags=["net-worth"])


def _to_decimal(x: float) -> Decimal:
    return Decimal(str(x))


def _parse_asset_category(raw: str) -> AssetCategory:
    s = raw.strip().upper()

    if s in {"FINANCIER", "FINANCIAL"}:
        return AssetCategory.FINANCIAL
    if s in {"IMMO", "IMMOBILIER", "REAL_ESTATE", "REALESTATE"}:
        return AssetCategory.REAL_ESTATE
    if s in {"PHYSIQUE", "PHYSICAL"}:
        return AssetCategory.PHYSICAL

    raise ValueError(f"Unknown asset category: {raw}")


@router.post("/compute", response_model=NetWorthComputeResponse)
def compute_net_worth_endpoint(payload: NetWorthComputeRequest) -> NetWorthComputeResponse:
    domain_assets: list[Asset] = []
    for a in payload.assets:
        category = _parse_asset_category(a.category)
        value = Money(amount=_to_decimal(a.value.amount), currency=a.value.currency)
        domain_assets.append(Asset.create(name=a.name, category=category, value=value))

    domain_liabilities: list[Liability] = []
    for l in payload.liabilities:
        balance = Money(amount=_to_decimal(l.balance.amount), currency=l.balance.currency)
        domain_liabilities.append(Liability.create(name=l.name, balance=balance))

    result = compute_net_worth(domain_assets, domain_liabilities)

    assets_total_out = {
        c: MoneyOut(amount=float(m.amount), currency=m.currency)
        for c, m in result.assets_total.items()
    }
    liabilities_total_out = {
        c: MoneyOut(amount=float(m.amount), currency=m.currency)
        for c, m in result.liabilities_total.items()
    }
    net_total_out = {
        c: SignedMoneyOut(amount=float(sm.amount), currency=sm.currency)
        for c, sm in result.net_total.items()
    }

    return NetWorthComputeResponse(
        assets_total=assets_total_out,
        liabilities_total=liabilities_total_out,
        net_total=net_total_out,
    )
