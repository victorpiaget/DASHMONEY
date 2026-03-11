"""
Tests d'isolation par profile_id sur les ressources non-account :
- Transactions
- Portfolios + Snapshots
- Trades
- Net worth scoped par profil
"""
from __future__ import annotations

from app.identity.defaults import DEFAULT_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_profile(client, display_name="Other Profile"):
    r = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/profiles",
        json={"display_name": display_name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_account(client, account_id, *, profile_id=None, currency="EUR", opening="0.00"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": currency,
        "opening_balance": opening,
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": profile_id,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _add_tx(client, account_id, *, profile_id=None, amount="-10.00", kind="EXPENSE"):
    r = client.post(
        f"/accounts/{account_id}/transactions",
        params={"profile_id": profile_id} if profile_id else {},
        json={
            "date": "2026-01-10",
            "amount": amount,
            "kind": kind,
            "category": "food",
            "subcategory": None,
            "label": None,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_portfolio(client, *, profile_id=None, name="PEA"):
    params = {"profile_id": profile_id} if profile_id else {}
    r = client.post("/portfolios", params=params, json={
        "name": name,
        "currency": "EUR",
        "portfolio_type": "PEA",
        "opened_on": "2026-01-01",
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Transactions isolées par profil
# ---------------------------------------------------------------------------

def test_transactions_isolated_by_profile(client):
    other_pid = _create_profile(client, "ISO TX Profile")

    # compte dans profil par défaut
    _create_account(client, "ISO_TX_A")
    _add_tx(client, "ISO_TX_A", amount="-100.00", kind="EXPENSE")

    # compte dans autre profil
    _create_account(client, "ISO_TX_B", profile_id=other_pid)
    _add_tx(client, "ISO_TX_B", profile_id=other_pid, amount="-200.00", kind="EXPENSE")

    # le profil par défaut ne voit que ses propres transactions
    txs_default = client.get("/accounts/ISO_TX_A/transactions").json()
    assert len(txs_default) == 1
    assert txs_default[0]["amount"] == "-100.00"

    # l'autre profil ne voit que ses propres transactions
    txs_other = client.get(
        "/accounts/ISO_TX_B/transactions",
        params={"profile_id": other_pid},
    ).json()
    assert len(txs_other) == 1
    assert txs_other[0]["amount"] == "-200.00"


def test_cannot_access_other_profile_account_transactions(client):
    """Tenter d'accéder au compte d'un autre profil sans le bon profile_id => 404."""
    other_pid = _create_profile(client, "CROSS TX")
    _create_account(client, "CROSS_ACC", profile_id=other_pid)

    # sans profile_id (défaut) => compte appartient à other_pid => 404
    r = client.get("/accounts/CROSS_ACC/transactions")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Net worth scopé par profil
# ---------------------------------------------------------------------------

def test_net_worth_scoped_by_profile(client):
    other_pid = _create_profile(client, "NW ISO Profile")

    _create_account(client, "NW_ISO_A", opening="1000.00")
    _create_account(client, "NW_ISO_B", profile_id=other_pid, opening="5000.00")

    # net worth du profil par défaut => 1000 seulement
    r = client.get("/net-worth")
    assert r.status_code == 200
    assert r.json()["net_worth"] == "1000.00"

    # net worth de l'autre profil => 5000
    r2 = client.get("/net-worth", params={"profile_id": other_pid})
    assert r2.status_code == 200
    assert r2.json()["net_worth"] == "5000.00"


# ---------------------------------------------------------------------------
# Portfolios isolés par profil
# ---------------------------------------------------------------------------

def test_portfolios_isolated_by_profile(client):
    other_pid = _create_profile(client, "PF ISO Profile")

    _create_portfolio(client, name="Default PEA")
    _create_portfolio(client, name="Other PEA", profile_id=other_pid)

    # liste profil par défaut => ne voit pas Other PEA
    r = client.get("/portfolios")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Default PEA" in names
    assert "Other PEA" not in names

    # liste autre profil => ne voit pas Default PEA
    r2 = client.get("/portfolios", params={"profile_id": other_pid})
    assert r2.status_code == 200
    names2 = [p["name"] for p in r2.json()]
    assert "Other PEA" in names2
    assert "Default PEA" not in names2


def test_cannot_access_other_profile_portfolio(client):
    other_pid = _create_profile(client, "PF CROSS Profile")
    p = _create_portfolio(client, name="CROSS PEA", profile_id=other_pid)

    # accès sans profile_id => 404 (appartient à other_pid)
    r = client.get(f"/portfolios/{p['id']}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Trades isolés par profil
# ---------------------------------------------------------------------------

def test_trades_isolated_by_profile(client):
    other_pid = _create_profile(client, "TRADE ISO Profile")

    # instrument global (pas de scoping sur instruments)
    client.post("/instruments", json={"symbol": "ISO_INST", "kind": "STOCK", "currency": "EUR"})

    # portfolio profil par défaut
    p_default = _create_portfolio(client, name="Default Trade PEA")
    r = client.post(f"/portfolios/{p_default['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "ISO_INST",
        "quantity": "10",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 201, r.text

    # portfolio autre profil
    p_other = _create_portfolio(client, name="Other Trade PEA", profile_id=other_pid)
    r2 = client.post(
        f"/portfolios/{p_other['id']}/trades",
        params={"profile_id": other_pid},
        json={
            "date": "2026-01-10",
            "side": "BUY",
            "instrument_symbol": "ISO_INST",
            "quantity": "20",
            "price": "100.00",
            "fees": "0.00",
            "label": None,
        },
    )
    assert r2.status_code == 201, r2.text

    # trades profil par défaut
    from decimal import Decimal
    r_trades = client.get(f"/portfolios/{p_default['id']}/trades").json()
    assert len(r_trades) == 1
    assert Decimal(r_trades[0]["quantity"]) == Decimal("10")

    # trades autre profil
    r_trades2 = client.get(
        f"/portfolios/{p_other['id']}/trades",
        params={"profile_id": other_pid},
    ).json()
    assert len(r_trades2) == 1
    assert Decimal(r_trades2[0]["quantity"]) == Decimal("20")


# ---------------------------------------------------------------------------
# Balance scopée par profil
# ---------------------------------------------------------------------------

def test_balance_scoped_by_profile(client):
    other_pid = _create_profile(client, "BAL ISO Profile")

    _create_account(client, "BAL_ISO_A", opening="1000.00")
    _create_account(client, "BAL_ISO_B", profile_id=other_pid, opening="3000.00")

    # balance compte du profil par défaut
    r = client.get("/accounts/BAL_ISO_A/balance")
    assert r.status_code == 200
    assert r.json()["balance"] == "1000.00"

    # compte de l'autre profil non accessible sans le profile_id
    r2 = client.get("/accounts/BAL_ISO_B/balance")
    assert r2.status_code == 404
