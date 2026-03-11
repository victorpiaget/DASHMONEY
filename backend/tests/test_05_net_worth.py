"""
Tests pour les endpoints /net-worth :
  GET /net-worth
  GET /net-worth/timeseries
  GET /net-worth/grouped
  GET /net-worth/timeseries/grouped
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_account(client, account_id: str, *, currency="EUR", opening="0.00", account_type="CHECKING"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": currency,
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


# ---------------------------------------------------------------------------
# /net-worth (snapshot)
# ---------------------------------------------------------------------------

def test_net_worth_no_accounts_returns_zero(client):
    r = client.get("/net-worth")
    assert r.status_code == 200
    data = r.json()
    from decimal import Decimal
    assert Decimal(data["net_worth"]) == Decimal("0")
    assert data["currency"] == "EUR"


def test_net_worth_opening_balance_only(client):
    _create_account(client, "NW1", opening="500.00")

    r = client.get("/net-worth")
    assert r.status_code == 200
    assert r.json()["net_worth"] == "500.00"


def test_net_worth_with_transactions(client):
    _create_account(client, "NW2", opening="1000.00")
    _add_tx(client, "NW2", date="2026-01-10", amount="-200.00", kind="EXPENSE")
    _add_tx(client, "NW2", date="2026-01-15", amount="300.00", kind="INCOME", category="salary")

    r = client.get("/net-worth")
    assert r.status_code == 200
    # 1000 - 200 + 300 = 1100
    assert r.json()["net_worth"] == "1100.00"


def test_net_worth_at_date_excludes_future_txs(client):
    _create_account(client, "NW3", opening="500.00")
    _add_tx(client, "NW3", date="2026-01-05", amount="-50.00", kind="EXPENSE")
    _add_tx(client, "NW3", date="2026-03-01", amount="-999.00", kind="EXPENSE")

    r = client.get("/net-worth", params={"at": "2026-01-31"})
    assert r.status_code == 200
    # 500 - 50 = 450, tx de mars exclue
    assert r.json()["net_worth"] == "450.00"


def test_net_worth_filter_by_account_type(client):
    _create_account(client, "NW_CHK", opening="1000.00", account_type="CHECKING")
    _create_account(client, "NW_SAV", opening="2000.00", account_type="SAVINGS")

    # sans filtre => 3000
    r_all = client.get("/net-worth")
    assert r_all.status_code == 200
    assert r_all.json()["net_worth"] == "3000.00"

    # filtre CHECKING seulement => 1000
    r_chk = client.get("/net-worth", params={"types": "CHECKING"})
    assert r_chk.status_code == 200
    assert r_chk.json()["net_worth"] == "1000.00"

    # filtre SAVINGS seulement => 2000
    r_sav = client.get("/net-worth", params={"types": "SAVINGS"})
    assert r_sav.status_code == 200
    assert r_sav.json()["net_worth"] == "2000.00"


def test_net_worth_invalid_account_type_returns_422(client):
    r = client.get("/net-worth", params={"types": "INVALID_TYPE"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /net-worth/timeseries
# ---------------------------------------------------------------------------

def test_net_worth_timeseries_basic(client):
    _create_account(client, "NWT1", opening="1000.00")
    _add_tx(client, "NWT1", date="2026-01-15", amount="-100.00", kind="EXPENSE")

    r = client.get("/net-worth/timeseries", params={"from": "2026-01-01", "to": "2026-01-31"})
    assert r.status_code == 200
    data = r.json()

    assert "points" in data
    assert data["granularity"] in ("daily", "weekly", "monthly", "yearly")
    assert len(data["points"]) > 0

    # chaque point a les bons champs
    p = data["points"][0]
    for field in ("bucket", "income", "expense", "net", "balance_start", "balance_end"):
        assert field in p, f"champ manquant: {field}"


def test_net_worth_timeseries_from_greater_than_to_returns_422(client):
    r = client.get("/net-worth/timeseries", params={"from": "2026-02-01", "to": "2026-01-01"})
    assert r.status_code == 422


def test_net_worth_timeseries_granularity_monthly(client):
    _create_account(client, "NWT2", opening="0.00")
    _add_tx(client, "NWT2", date="2026-01-10", amount="100.00", kind="INCOME", category="salary")
    _add_tx(client, "NWT2", date="2026-02-10", amount="200.00", kind="INCOME", category="salary")

    r = client.get("/net-worth/timeseries", params={
        "from": "2026-01-01", "to": "2026-02-28", "granularity": "monthly"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["granularity"] == "monthly"
    assert len(data["points"]) == 2


# ---------------------------------------------------------------------------
# /net-worth/grouped
# ---------------------------------------------------------------------------

def test_net_worth_grouped_by_account_type(client):
    _create_account(client, "NWG1", opening="1000.00", account_type="CHECKING")
    _create_account(client, "NWG2", opening="500.00", account_type="SAVINGS")

    r = client.get("/net-worth/grouped")
    assert r.status_code == 200
    data = r.json()

    assert "total" in data
    assert "groups" in data
    assert data["total"] == "1500.00"

    keys = {g["key"] for g in data["groups"]}
    assert "CHECKING" in keys
    assert "SAVINGS" in keys

    chk = next(g for g in data["groups"] if g["key"] == "CHECKING")
    sav = next(g for g in data["groups"] if g["key"] == "SAVINGS")
    assert chk["net_worth"] == "1000.00"
    assert sav["net_worth"] == "500.00"


def test_net_worth_grouped_no_accounts(client):
    r = client.get("/net-worth/grouped")
    assert r.status_code == 200
    data = r.json()
    from decimal import Decimal
    assert Decimal(data["total"]) == Decimal("0")
    assert data["groups"] == []


# ---------------------------------------------------------------------------
# /net-worth/timeseries/grouped
# ---------------------------------------------------------------------------

def test_net_worth_timeseries_grouped_structure(client):
    _create_account(client, "NWTG1", opening="1000.00", account_type="CHECKING")
    _create_account(client, "NWTG2", opening="500.00", account_type="SAVINGS")
    _add_tx(client, "NWTG1", date="2026-01-10", amount="-100.00", kind="EXPENSE")

    r = client.get("/net-worth/timeseries/grouped", params={
        "from": "2026-01-01", "to": "2026-01-31", "granularity": "monthly"
    })
    assert r.status_code == 200
    data = r.json()

    assert "total_points" in data
    assert "groups" in data
    assert len(data["total_points"]) > 0
    assert len(data["groups"]) > 0

    for g in data["groups"]:
        assert "key" in g
        assert "points" in g


def test_net_worth_timeseries_grouped_from_greater_than_to_returns_422(client):
    r = client.get("/net-worth/timeseries/grouped", params={"from": "2026-02-01", "to": "2026-01-01"})
    assert r.status_code == 422
