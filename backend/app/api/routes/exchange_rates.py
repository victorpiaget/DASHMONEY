from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.domain.user import User
from app.repositories.sql_exchange_rate_repository import SqlExchangeRateRepository
from app.services.update_exchange_rates_service import update_exchange_rates

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("/latest", response_model=dict[str, float])
def get_latest_rates():
    """Retourne tous les taux de change avec EUR comme devise de base.
    Convention : 1 EUR = rate[currency]
    Ex : {"EUR": 1.0, "USD": 1.08, "BTC": 0.0000152}
    Si aucun taux en base, tente une mise à jour synchrone.
    """
    repo = SqlExchangeRateRepository()
    rates = repo.get_all()

    if len(rates) <= 1:
        # Seulement EUR seedé par la migration → fetch synchrone au premier appel
        try:
            update_exchange_rates()
            rates = repo.get_all()
        except Exception:
            pass

    if len(rates) <= 1:
        raise HTTPException(
            status_code=503,
            detail="Taux de change indisponibles. Réessayez dans quelques instants.",
        )

    # Garantir EUR = 1.0
    rates["EUR"] = 1.0
    return rates


@router.post("/update", response_model=dict)
def trigger_update(_user: User = Depends(get_current_user)):
    """Force une mise à jour manuelle des taux de change (authentifié)."""
    result = update_exchange_rates()
    return {"stored": result["stored"], "failed": result["failed"]}
