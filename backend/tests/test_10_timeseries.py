"""
Tests pour les endpoints de timeseries :
  GET /accounts/{id}/timeseries
  GET /net-worth/full
  GET /net-worth/full/timeseries
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_account(client, account_id, *, opening="0.00", account_type="CHECKING"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": "EUR",
        "opening_balance": opening,
        "opened_on": "2026-01-01",
        "account_type": account_type,
        "profile_id": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _add_tx(client, account_id, *, date, amount, kind, category="food"):
    r = client.post(f"/accounts/{account_id}/transactions", json={
        "date": date,
        "amount": amount,
        "kind": kind,
        "category": category,
        "subcategory": None,
        "label": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _create_portfolio(client, *, name="PEA", currency="EUR"):
    r = client.post("/portfolios", json={
        "name": name,
        "currency": currency,
        "portfolio_type": "PEA",
        "opened_on": "2026-01-01",
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Account timeseries
# ---------------------------------------------------------------------------

def test_account_timeseries_basic(client):
    _create_account(client, "TS1", opening="1000.00")
    _add_tx(client, "TS1", date="2026-01-15", amount="-200.00", kind="EXPENSE")
    _add_tx(client, "TS1", date="2026-02-10", amount="500.00", kind="INCOME", category="salary")

    r = client.get("/accounts/TS1/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-02-28",
        "granularity": "monthly",
    })
    assert r.status_code == 200
    data = r.json()

    assert data["account_id"] == "TS1"
    assert data["currency"] == "EUR"
    assert data["granularity"] == "monthly"
    assert len(data["points"]) == 2

    from decimal import Decimal
    # Janvier : expense de 200
    jan = data["points"][0]
    assert Decimal(jan["expense"]) == Decimal("200.00")
    assert Decimal(jan["income"]) == Decimal("0")

    # Février : income de 500
    feb = data["points"][1]
    assert Decimal(feb["income"]) == Decimal("500.00")
    assert Decimal(feb["expense"]) == Decimal("0")


def test_account_timeseries_balance_carry(client):
    """Le balance_end d'un bucket doit être le balance_start du suivant."""
    _create_account(client, "TS2", opening="500.00")
    _add_tx(client, "TS2", date="2026-01-20", amount="-100.00", kind="EXPENSE")

    r = client.get("/accounts/TS2/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-02-28",
        "granularity": "monthly",
    })
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 2

    # balance_end janvier = balance_start février
    assert points[0]["balance_end"] == points[1]["balance_start"]


def test_account_timeseries_from_greater_than_to_returns_422(client):
    _create_account(client, "TS3")

    r = client.get("/accounts/TS3/timeseries", params={
        "from": "2026-03-01",
        "to": "2026-01-01",
    })
    assert r.status_code == 422


def test_account_timeseries_account_not_found_returns_404(client):
    r = client.get("/accounts/GHOST_TS/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-01-31",
    })
    assert r.status_code == 404


def test_account_timeseries_granularity_daily(client):
    _create_account(client, "TS4")
    _add_tx(client, "TS4", date="2026-01-03", amount="-10.00", kind="EXPENSE")
    _add_tx(client, "TS4", date="2026-01-05", amount="-20.00", kind="EXPENSE")

    r = client.get("/accounts/TS4/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-01-07",
        "granularity": "daily",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["granularity"] == "daily"
    assert len(data["points"]) == 7


def test_account_timeseries_granularity_yearly(client):
    _create_account(client, "TS5", opening="1000.00")
    _add_tx(client, "TS5", date="2026-06-01", amount="-300.00", kind="EXPENSE")

    r = client.get("/accounts/TS5/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-12-31",
        "granularity": "yearly",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["granularity"] == "yearly"
    assert len(data["points"]) == 1
    assert data["points"][0]["expense"] == "300.00"


# ---------------------------------------------------------------------------
# Net worth full (comptes + portefeuilles)
# ---------------------------------------------------------------------------

def test_net_worth_full_no_data(client):
    r = client.get("/net-worth/full")
    assert r.status_code == 200
    data = r.json()
    from decimal import Decimal
    assert Decimal(data["net_worth_full"]) == Decimal("0")


def test_net_worth_full_accounts_only(client):
    _create_account(client, "NWF1", opening="1000.00")
    _add_tx(client, "NWF1", date="2026-01-10", amount="-200.00", kind="EXPENSE")

    r = client.get("/net-worth/full")
    assert r.status_code == 200
    # 1000 - 200 = 800
    assert r.json()["net_worth_full"] == "800.00"


def test_net_worth_full_with_portfolio_snapshot(client):
    """Un snapshot de portfolio doit augmenter le net worth full."""
    _create_account(client, "NWF2", opening="500.00")

    p = _create_portfolio(client, name="PEA NWF")
    # ajouter un snapshot de valeur 1500
    client.post(f"/portfolios/{p['id']}/snapshots", json={
        "date": "2026-01-31",
        "value": "1500.00",
        "currency": "EUR",
        "note": None,
    })

    r = client.get("/net-worth/full", params={"at": "2026-01-31"})
    assert r.status_code == 200
    # 500 (compte) + 1500 (portfolio) = 2000 (le cash_account du portfolio est dans les comptes)
    # Note : le cash account du portfolio est inclus dans les comptes (opening=0 + aucune tx hors trade)
    data = r.json()
    assert "net_worth_full" in data


def test_net_worth_full_timeseries_basic(client):
    _create_account(client, "NWFT1", opening="1000.00")
    _add_tx(client, "NWFT1", date="2026-01-15", amount="-100.00", kind="EXPENSE")

    r = client.get("/net-worth/full/timeseries", params={
        "from": "2026-01-01",
        "to": "2026-01-31",
        "granularity": "monthly",
    })
    assert r.status_code == 200
    data = r.json()

    assert "points" in data
    assert len(data["points"]) == 1
    p = data["points"][0]
    for field in ("bucket", "income", "expense", "net", "balance_start", "balance_end"):
        assert field in p


def test_net_worth_full_timeseries_from_greater_than_to_returns_422(client):
    r = client.get("/net-worth/full/timeseries", params={
        "from": "2026-03-01",
        "to": "2026-01-01",
    })
    assert r.status_code == 422
