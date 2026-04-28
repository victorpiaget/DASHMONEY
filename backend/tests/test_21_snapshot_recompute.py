"""
Tests pour la logique de recompute des snapshots après mutation de trades.

Scénario clé : un trade ajouté aujourd'hui mais daté dans le passé doit
provoquer un recalcul de tous les snapshots à partir de cette date — sinon
la courbe de valorisation est déconnectée de la réalité.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.domain.money import Currency
from app.domain.price_point import PricePoint
from app.identity.defaults import DEFAULT_PROFILE_ID
from app.repositories.sql_price_repository import SqlPriceRepository
from app.repositories.sql_portfolio_snapshot_repository import SqlPortfolioSnapshotRepository


def _create_instrument(client, symbol, *, kind="STOCK", currency="EUR"):
    r = client.post("/instruments", json={"symbol": symbol, "kind": kind, "currency": currency})
    assert r.status_code == 201, r.text
    return r.json()


def _create_portfolio(client, *, name="Recompute PEA"):
    r = client.post("/portfolios", json={
        "name": name,
        "currency": "EUR",
        "portfolio_type": "PEA",
        "opened_on": "2026-01-01",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _seed_price(symbol: str, day: dt.date, amount: str) -> None:
    """Ajoute directement un PricePoint en base (bypass yfinance)."""
    repo = SqlPriceRepository()
    try:
        repo.add(PricePoint(
            symbol=symbol.upper(),
            day=day,
            price=Decimal(amount),
            currency=Currency.EUR,
            source="test",
            captured_at=dt.datetime.now(dt.timezone.utc),
        ))
    except Exception:
        pass  # duplicate ignored


@pytest.fixture
def no_network_backfill(monkeypatch):
    """Neutralise backfill_prices pour éviter les appels yfinance/Binance en test."""
    from app.services import snapshot_recompute_service

    def _noop(**kwargs):
        return {"stored": 0, "skipped": 0}

    monkeypatch.setattr(snapshot_recompute_service, "backfill_prices", _noop)


def test_retroactive_trade_recomputes_past_snapshots(client, no_network_backfill):
    """
    Un trade créé aujourd'hui mais daté d'il y a 5 jours doit déclencher
    le recompute : des snapshots doivent apparaître à ces dates passées.
    """
    today = dt.date.today()
    past = today - dt.timedelta(days=5)

    p = _create_portfolio(client, name="Retro")
    _create_instrument(client, "RECALC_INS")

    # Pré-peuple les prix historiques pour les 6 jours concernés
    for i in range(6):
        _seed_price("RECALC_INS", past + dt.timedelta(days=i), "100.00")

    # Avant le trade : aucun snapshot
    snap_repo = SqlPortfolioSnapshotRepository()
    before = snap_repo.list(portfolio_id=p["id"], profile_id=DEFAULT_PROFILE_ID)
    assert len(before) == 0

    # Trade BUY daté d'il y a 5 jours → 10 titres × 100€
    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": past.isoformat(),
        "side": "BUY",
        "instrument_symbol": "RECALC_INS",
        "quantity": "10",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 201, r.text

    # Le BackgroundTask de TestClient est exécuté avant que .post() ne revienne
    after = snap_repo.list(portfolio_id=p["id"], profile_id=DEFAULT_PROFILE_ID)
    assert len(after) >= 6, f"attendu ≥ 6 snapshots (past→today), obtenu {len(after)}"

    # Tous les snapshots couvrent bien la plage [past, today]
    days = {s.date for s in after}
    for i in range(6):
        assert (past + dt.timedelta(days=i)) in days

    # Chaque snapshot vaut 10 × 100 = 1000 EUR
    for s in after:
        assert s.value.amount == Decimal("1000"), f"snapshot {s.date} = {s.value.amount}"


def test_delete_trade_recomputes_and_removes_stale_value(client, no_network_backfill):
    """
    Après suppression d'un trade rétroactif, les snapshots passés doivent
    être recalculés : sans position, plus de snapshot (ou snapshots à 0).
    """
    today = dt.date.today()
    past = today - dt.timedelta(days=3)

    p = _create_portfolio(client, name="DeleteRetro")
    _create_instrument(client, "DEL_INS")

    for i in range(4):
        _seed_price("DEL_INS", past + dt.timedelta(days=i), "50.00")

    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": past.isoformat(),
        "side": "BUY",
        "instrument_symbol": "DEL_INS",
        "quantity": "5",
        "price": "50.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 201
    trade_id = r.json()["id"]

    snap_repo = SqlPortfolioSnapshotRepository()
    assert len(snap_repo.list(portfolio_id=p["id"], profile_id=DEFAULT_PROFILE_ID)) >= 4

    # Suppression du trade → recompute → plus de positions → plus de snapshots
    r = client.delete(f"/portfolios/{p['id']}/trades/{trade_id}")
    assert r.status_code == 204, r.text

    after = snap_repo.list(portfolio_id=p["id"], profile_id=DEFAULT_PROFILE_ID)
    assert len(after) == 0, f"snapshots devaient être supprimés, reste: {after}"


def test_manual_recompute_endpoint(client, no_network_backfill):
    """
    POST /snapshots/portfolio/{id}/recompute?from=... doit fonctionner
    de manière synchrone et retourner un récap.
    """
    today = dt.date.today()
    past = today - dt.timedelta(days=2)

    p = _create_portfolio(client, name="Manual")
    _create_instrument(client, "MAN_INS")
    for i in range(3):
        _seed_price("MAN_INS", past + dt.timedelta(days=i), "200.00")

    client.post(f"/portfolios/{p['id']}/trades", json={
        "date": past.isoformat(),
        "side": "BUY",
        "instrument_symbol": "MAN_INS",
        "quantity": "2",
        "price": "200.00",
        "fees": "0.00",
        "label": None,
    })

    r = client.post(
        f"/snapshots/portfolio/{p['id']}/recompute",
        params={"from": past.isoformat()},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["portfolio_id"] == p["id"]
    assert body["from_date"] == past.isoformat()
    assert body["created"] >= 3
