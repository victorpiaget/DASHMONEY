"""
Tests pour /snapshots :
  GET    /snapshots/pnl-curve
  POST   /snapshots/auto
  POST   /snapshots/backfill
  DELETE /snapshots/portfolio/{portfolio_id}
"""
from __future__ import annotations

import datetime as dt


def _create_instrument(client, symbol, *, kind="STOCK", currency="EUR"):
    r = client.post("/instruments", json={"symbol": symbol, "kind": kind, "currency": currency})
    assert r.status_code == 201, r.text
    return r.json()


def _create_portfolio(client, *, name="Snap PEA", currency="EUR"):
    r = client.post("/portfolios", json={
        "name": name,
        "currency": currency,
        "portfolio_type": "PEA",
        "opened_on": "2026-01-01",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _buy(client, portfolio_id, symbol, *, qty, price="100.00", date="2026-01-10"):
    r = client.post(f"/portfolios/{portfolio_id}/trades", json={
        "date": date,
        "side": "BUY",
        "instrument_symbol": symbol,
        "quantity": str(qty),
        "price": str(price),
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _add_manual_snapshot(client, portfolio_id, *, date, value, currency="EUR"):
    r = client.post(f"/portfolios/{portfolio_id}/snapshots", json={
        "date": date,
        "value": value,
        "currency": currency,
        "note": None,
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------


def test_pnl_curve_empty_no_snapshots(client):
    r = client.get("/snapshots/pnl-curve")
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_pnl_curve_basic(client):
    p = _create_portfolio(client, name="PNL Basic")
    _create_instrument(client, "SNAP_INS")
    _buy(client, p["id"], "SNAP_INS", qty=10, price="100.00", date="2026-01-10")

    _add_manual_snapshot(client, p["id"], date="2026-01-31", value="1200.00")

    r = client.get("/snapshots/pnl-curve")
    assert r.status_code == 200, r.text
    points = r.json()
    assert len(points) == 1
    pt = points[0]
    assert pt["date"] == "2026-01-31"
    assert pt["portfolio_value"] == 1200.0
    assert pt["net_invested"] == 1000.0  # 10 * 100
    assert pt["pnl"] == 200.0


def test_pnl_curve_isolation(client, auth_headers_user2):
    from fastapi.testclient import TestClient
    from app.api.main import app

    p = _create_portfolio(client, name="IsolSnap")
    _create_instrument(client, "SNAP_ISO")
    _buy(client, p["id"], "SNAP_ISO", qty=5, price="100.00")
    _add_manual_snapshot(client, p["id"], date="2026-01-31", value="600.00")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r2 = c2.get("/snapshots/pnl-curve")

    assert r2.status_code == 200, r2.text
    assert r2.json() == []


def test_auto_snapshot_no_positions_skipped(client):
    p = _create_portfolio(client, name="EmptySnap")

    today = dt.date.today().isoformat()
    r = client.post("/snapshots/auto", params={"day": today})
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["skipped"] >= 1
    assert result["created"] == 0


def test_auto_snapshot_with_positions(client):
    p = _create_portfolio(client, name="AutoSnapP")
    _create_instrument(client, "SNAP_AUTO")
    _buy(client, p["id"], "SNAP_AUTO", qty=5, price="100.00")

    today = dt.date.today().isoformat()
    r = client.post("/snapshots/auto", params={"day": today})
    assert r.status_code == 200, r.text
    result = r.json()
    # Peut être skipped si pas de prix en base — on vérifie juste que l'endpoint répond 200
    assert "created" in result
    assert "skipped" in result
    assert "errors" in result


def test_backfill_snapshots_idempotent(client):
    """Deux backfill identiques ne doublent pas les snapshots (le second est entierement skipped)."""
    p = _create_portfolio(client, name="BackfillP")
    _create_instrument(client, "SNAP_BF")
    _buy(client, p["id"], "SNAP_BF", qty=3, price="50.00", date="2026-01-05")

    params = {"date_from": "2026-01-10", "date_to": "2026-01-11"}
    r1 = client.post("/snapshots/backfill", params=params)
    assert r1.status_code == 200, r1.text
    r1_data = r1.json()

    r2 = client.post("/snapshots/backfill", params=params)
    assert r2.status_code == 200, r2.text
    r2_data = r2.json()

    # Le second backfill ne peut pas créer plus de snapshots qu'il n'y en a au total
    assert r2_data["created"] == 0
    assert r2_data["skipped"] >= r1_data["created"]


def test_delete_portfolio_snapshots(client):
    p = _create_portfolio(client, name="DelSnap")
    for date, value in [("2026-01-31", "100.00"), ("2026-02-28", "200.00")]:
        _add_manual_snapshot(client, p["id"], date=date, value=value)

    snaps_before = client.get(f"/portfolios/{p['id']}/snapshots").json()
    assert len(snaps_before) == 2

    r = client.delete(f"/snapshots/portfolio/{p['id']}")
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["deleted"] == 2

    snaps_after = client.get(f"/portfolios/{p['id']}/snapshots").json()
    assert snaps_after == []
