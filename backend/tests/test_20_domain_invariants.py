"""
Tests des invariants metier via l'API — verifie que le domaine
rejette les entrees invalides avec un 422.
"""
from __future__ import annotations


def _create_account(client, account_id, *, currency="EUR"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": "Account",
        "currency": currency,
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
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


def _create_instrument(client, symbol, *, currency="EUR"):
    r = client.post("/instruments", json={"symbol": symbol, "kind": "STOCK", "currency": currency})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Transaction invariants
# ---------------------------------------------------------------------------

def test_transaction_amount_zero_returns_422(client):
    _create_account(client, "INV_TX_ZERO")
    r = client.post("/accounts/INV_TX_ZERO/transactions", json={
        "date": "2026-01-10",
        "amount": "0.00",
        "kind": "EXPENSE",
        "category": "food",
        "subcategory": None,
        "label": "zero",
    })
    assert r.status_code == 422, r.text


def test_transaction_positive_amount_expense_returns_422(client):
    """Montant positif avec kind=EXPENSE doit etre rejete."""
    _create_account(client, "INV_TX_POS_EXP")
    r = client.post("/accounts/INV_TX_POS_EXP/transactions", json={
        "date": "2026-01-10",
        "amount": "50.00",
        "kind": "EXPENSE",
        "category": "food",
        "subcategory": None,
        "label": "bad",
    })
    assert r.status_code == 422, r.text


def test_transaction_negative_amount_income_returns_422(client):
    """Montant negatif avec kind=INCOME doit etre rejete."""
    _create_account(client, "INV_TX_NEG_INC")
    r = client.post("/accounts/INV_TX_NEG_INC/transactions", json={
        "date": "2026-01-10",
        "amount": "-50.00",
        "kind": "INCOME",
        "category": "salary",
        "subcategory": None,
        "label": "bad",
    })
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Trade invariants
# ---------------------------------------------------------------------------

def test_trade_quantity_zero_returns_422(client):
    _create_instrument(client, "INV_QTY_ZERO")
    p = _create_portfolio(client, name="InvQty")
    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "INV_QTY_ZERO",
        "quantity": "0",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 422, r.text


def test_trade_price_zero_returns_422(client):
    _create_instrument(client, "INV_PRICE_ZERO")
    p = _create_portfolio(client, name="InvPrice")
    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "INV_PRICE_ZERO",
        "quantity": "1",
        "price": "0",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 422, r.text


def test_trade_fees_negative_returns_422(client):
    _create_instrument(client, "INV_FEES_NEG")
    p = _create_portfolio(client, name="InvFees")
    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "INV_FEES_NEG",
        "quantity": "1",
        "price": "100.00",
        "fees": "-5.00",
        "label": None,
    })
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Virement (transfer entre comptes) invariants
# ---------------------------------------------------------------------------

def test_virement_amount_zero_returns_422(client):
    _create_account(client, "INV_VIR_SRC")
    _create_account(client, "INV_VIR_DST")
    r = client.post("/accounts/INV_VIR_SRC/transfers", json={
        "to_account_id": "INV_VIR_DST",
        "amount": "0.00",
        "date": "2026-01-10",
        "category": "transfer",
        "subcategory": None,
        "label": None,
    })
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Account invariants
# ---------------------------------------------------------------------------

def test_account_duplicate_id_returns_409(client):
    _create_account(client, "INV_DUP_ID")
    r = client.post("/accounts", json={
        "id": "INV_DUP_ID",
        "name": "Duplicate",
        "currency": "EUR",
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    })
    assert r.status_code == 409, r.text
