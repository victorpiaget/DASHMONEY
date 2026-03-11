"""
Tests pour les endpoints /portfolios :
  POST   /portfolios
  GET    /portfolios
  GET    /portfolios/{id}
  PATCH  /portfolios/{id}
  DELETE /portfolios/{id}
  POST   /portfolios/{id}/snapshots
  GET    /portfolios/{id}/snapshots
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_portfolio(client, *, name="Mon PEA", currency="EUR", portfolio_type="PEA", opened_on="2026-01-01"):
    r = client.post("/portfolios", json={
        "name": name,
        "currency": currency,
        "portfolio_type": portfolio_type,
        "opened_on": opened_on,
    })
    assert r.status_code == 200, r.text  # portfolios retourne 200 (pas 201)
    return r.json()


# ---------------------------------------------------------------------------
# CRUD portfolios
# ---------------------------------------------------------------------------

def test_create_portfolio_returns_portfolio_and_cash_account(client):
    p = _create_portfolio(client, name="PEA Test")

    assert "id" in p
    assert p["name"] == "PEA Test"
    assert p["currency"] == "EUR"
    assert p["portfolio_type"] == "PEA"
    assert "cash_account_id" in p
    assert p["cash_account_id"] is not None

    # le compte passerelle doit exister
    r = client.get("/accounts")
    ids = [a["id"] for a in r.json()]
    assert p["cash_account_id"] in ids


def test_list_portfolios(client):
    _create_portfolio(client, name="P1")
    _create_portfolio(client, name="P2")

    r = client.get("/portfolios")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "P1" in names
    assert "P2" in names


def test_get_portfolio_by_id(client):
    p = _create_portfolio(client, name="Detail Test")
    pid = p["id"]

    r = client.get(f"/portfolios/{pid}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == pid
    assert data["name"] == "Detail Test"


def test_get_portfolio_not_found_returns_404(client):
    r = client.get("/portfolios/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_update_portfolio_name_and_type(client):
    p = _create_portfolio(client, name="Old Name", portfolio_type="PEA")
    pid = p["id"]

    r = client.patch(f"/portfolios/{pid}", json={"name": "New Name", "portfolio_type": "CTO"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["name"] == "New Name"
    assert updated["portfolio_type"] == "CTO"


def test_update_portfolio_not_found_returns_404(client):
    r = client.patch(
        "/portfolios/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
    )
    assert r.status_code == 404


def test_delete_portfolio(client):
    p = _create_portfolio(client, name="To Delete")
    pid = p["id"]

    r = client.delete(f"/portfolios/{pid}")
    assert r.status_code == 200  # retourne {"deleted": True}

    r2 = client.get(f"/portfolios/{pid}")
    assert r2.status_code == 404


def test_delete_portfolio_not_found_returns_404(client):
    r = client.delete("/portfolios/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def test_add_and_list_snapshots(client):
    p = _create_portfolio(client, name="Snap Portfolio")
    pid = p["id"]

    r = client.post(f"/portfolios/{pid}/snapshots", json={
        "date": "2026-01-31",
        "value": "12345.67",
        "currency": "EUR",
        "note": "fin janvier",
    })
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["portfolio_id"] == pid
    assert snap["value"] == "12345.67"
    assert snap["date"] == "2026-01-31"
    assert snap["note"] == "fin janvier"

    r2 = client.get(f"/portfolios/{pid}/snapshots")
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 1
    assert items[0]["id"] == snap["id"]


def test_snapshot_currency_mismatch_returns_422(client):
    p = _create_portfolio(client, name="EUR Portfolio", currency="EUR")
    pid = p["id"]

    r = client.post(f"/portfolios/{pid}/snapshots", json={
        "date": "2026-01-31",
        "value": "1000.00",
        "currency": "USD",  # mauvaise devise
        "note": None,
    })
    assert r.status_code == 422


def test_snapshot_portfolio_not_found_returns_404(client):
    r = client.post("/portfolios/00000000-0000-0000-0000-000000000000/snapshots", json={
        "date": "2026-01-31",
        "value": "1000.00",
        "currency": "EUR",
        "note": None,
    })
    assert r.status_code == 404


def test_list_snapshots_with_date_filter(client):
    p = _create_portfolio(client, name="Snap Filter")
    pid = p["id"]

    # 3 snapshots sur des dates différentes
    for date, value in [("2026-01-31", "100.00"), ("2026-02-28", "200.00"), ("2026-03-31", "300.00")]:
        r = client.post(f"/portfolios/{pid}/snapshots", json={
            "date": date, "value": value, "currency": "EUR", "note": None,
        })
        assert r.status_code == 200, r.text

    # filtre from=2026-02-01
    r = client.get(f"/portfolios/{pid}/snapshots", params={"from": "2026-02-01"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    dates = {s["date"] for s in items}
    assert "2026-01-31" not in dates

    # filtre to=2026-02-28
    r2 = client.get(f"/portfolios/{pid}/snapshots", params={"to": "2026-02-28"})
    assert r2.status_code == 200
    items2 = r2.json()
    assert len(items2) == 2
    assert "2026-03-31" not in {s["date"] for s in items2}
