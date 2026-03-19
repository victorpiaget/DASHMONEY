"""
Tests pour GET /transactions (global, cross-comptes) :
  GET /transactions
"""
from __future__ import annotations

import datetime as dt


def _create_account(client, account_id, *, currency="EUR", name="Account"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": name,
        "currency": currency,
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _add_tx(client, account_id, *, date="2026-01-10", amount="-10.00", kind="EXPENSE",
            category="food", label="test"):
    r = client.post(f"/accounts/{account_id}/transactions", json={
        "date": date,
        "amount": amount,
        "kind": kind,
        "category": category,
        "subcategory": None,
        "label": label,
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_global_transactions_empty(client):
    r = client.get("/transactions")
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_global_transactions_contains_all_accounts(client):
    _create_account(client, "GLOB_ACC1", name="Compte A")
    _create_account(client, "GLOB_ACC2", name="Compte B")

    _add_tx(client, "GLOB_ACC1", label="tx from A")
    _add_tx(client, "GLOB_ACC2", label="tx from B")

    r = client.get("/transactions")
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 2
    account_ids = {tx["account_id"] for tx in items}
    assert "GLOB_ACC1" in account_ids
    assert "GLOB_ACC2" in account_ids


def test_global_transactions_filter_by_date(client):
    _create_account(client, "GLOB_DATE", name="DateFilter")
    _add_tx(client, "GLOB_DATE", date="2026-01-05", label="old")
    _add_tx(client, "GLOB_DATE", date="2026-02-10", label="new")

    r = client.get("/transactions", params={"date_from": "2026-02-01", "date_to": "2026-02-28"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["label"] == "new"


def test_global_transactions_filter_by_kind(client):
    _create_account(client, "GLOB_KIND", name="KindFilter")
    _add_tx(client, "GLOB_KIND", amount="-10.00", kind="EXPENSE", label="expense_tx")
    _add_tx(client, "GLOB_KIND", amount="50.00", kind="INCOME", label="income_tx")

    r = client.get("/transactions", params={"kinds": ["INCOME"]})
    assert r.status_code == 200, r.text
    items = r.json()
    assert all(tx["kind"] == "INCOME" for tx in items)
    labels = [tx["label"] for tx in items]
    assert "income_tx" in labels
    assert "expense_tx" not in labels


def test_global_transactions_filter_by_account_ids(client):
    _create_account(client, "GLOB_FILT1", name="FilterAcc1")
    _create_account(client, "GLOB_FILT2", name="FilterAcc2")

    _add_tx(client, "GLOB_FILT1", label="acc1_tx")
    _add_tx(client, "GLOB_FILT2", label="acc2_tx")

    r = client.get("/transactions", params={"account_ids": "GLOB_FILT1"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["account_id"] == "GLOB_FILT1"


def test_global_transactions_search_label(client):
    _create_account(client, "GLOB_Q", name="SearchAcc")
    _add_tx(client, "GLOB_Q", label="carrefour supermarche")
    _add_tx(client, "GLOB_Q", label="loyer mensuel")

    r = client.get("/transactions", params={"q": "carrefour"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert "carrefour" in items[0]["label"].lower()


def test_global_transactions_limit(client):
    _create_account(client, "GLOB_LIM", name="LimitAcc")
    for i in range(5):
        _add_tx(client, "GLOB_LIM", label=f"tx_{i}", date=f"2026-01-{10 + i:02d}")

    r = client.get("/transactions", params={"limit": 3})
    assert r.status_code == 200, r.text
    assert len(r.json()) == 3


def test_global_transactions_account_name_and_currency(client):
    _create_account(client, "GLOB_META", name="MonCompte", currency="EUR")
    _add_tx(client, "GLOB_META", label="meta_check")

    r = client.get("/transactions")
    assert r.status_code == 200, r.text
    items = r.json()
    item = next((tx for tx in items if tx["account_id"] == "GLOB_META"), None)
    assert item is not None
    assert item["account_name"] == "MonCompte"
    assert item["account_currency"] == "EUR"


def test_global_transactions_isolation(client, auth_headers_user2):
    from fastapi.testclient import TestClient
    from app.api.main import app

    _create_account(client, "GLOB_ISO1", name="IsoUser1")
    _add_tx(client, "GLOB_ISO1", label="user1_private")

    with TestClient(app) as c2:
        c2.headers.update(auth_headers_user2)
        r2 = c2.get("/transactions")

    assert r2.status_code == 200, r2.text
    items_u2 = r2.json()
    labels_u2 = [tx["label"] for tx in items_u2]
    assert "user1_private" not in labels_u2


def test_global_transactions_require_auth(client):
    from fastapi.testclient import TestClient
    from app.api.main import app

    with TestClient(app) as anon:
        r = anon.get("/transactions")
    assert r.status_code == 401, r.text
