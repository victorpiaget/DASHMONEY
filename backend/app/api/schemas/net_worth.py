# Pydantic sert à valider les données qui entrent/sortent de l'API (JSON <-> Python)
from pydantic import BaseModel, Field

# typing pour les types plus explicites
from typing import List, Dict

# On réutilise Currency du domain (EUR/USD)
from app.domain.money import Currency

# ----------------------------
# 1) Modèles "INPUT" (ce que le frontend va envoyer)
# ----------------------------

class MoneyIn(BaseModel):
    # amount : montant >= 0 (on laisse Money du domain faire la validation stricte,
    # mais on ajoute un garde-fou ici aussi)
    amount: float = Field(ge=0)
    currency: Currency


class AssetIn(BaseModel):
    # name : nom de l'actif
    name: str = Field(min_length=1)
    # category : on utilise une string ici pour l'API (simple pour V1),
    # on convertira vers AssetCategory dans la route
    category: str = Field(min_length=1)
    value: MoneyIn


class LiabilityIn(BaseModel):
    name: str = Field(min_length=1)
    balance: MoneyIn


class NetWorthComputeRequest(BaseModel):
    # Ce payload contient la liste d'actifs + la liste de dettes
    assets: List[AssetIn] = Field(default_factory=list)
    liabilities: List[LiabilityIn] = Field(default_factory=list)


# ----------------------------
# 2) Modèles "OUTPUT" (ce que l'API renvoie)
# ----------------------------

class MoneyOut(BaseModel):
    amount: float
    currency: Currency


class SignedMoneyOut(BaseModel):
    amount: float
    currency: Currency


class NetWorthComputeResponse(BaseModel):
    # Dict par devise (EUR/USD) -> Money
    assets_total: Dict[Currency, MoneyOut]
    liabilities_total: Dict[Currency, MoneyOut]
    net_total: Dict[Currency, SignedMoneyOut]
