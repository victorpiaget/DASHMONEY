"""
Tests pour les endpoints /instruments et /prices :
  POST   /instruments
  GET    /instruments
  DELETE /instruments/{symbol}
  GET    /prices
  GET    /prices/{symbol}/latest
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_instrument(client, symbol="AAPL", *, kind="STOCK", currency="EUR"):
    r = client.post("/instruments", json={
        "symbol": symbol,
        "kind": kind,
        "currency": currency,
    })
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------

def test_create_instrument(client):
    inst = _create_instrument(client, "AAPL")
    assert inst["symbol"] == "AAPL"
    assert inst["kind"] == "STOCK"
    assert inst["currency"] == "EUR"


def test_create_instrument_symbol_uppercased(client):
    # le symbole doit être normalisé en majuscules
    inst = _create_instrument(client, "msft")
    assert inst["symbol"] == "MSFT"


def test_create_instrument_duplicate_returns_409(client):
    _create_instrument(client, "TSLA")
    r = client.post("/instruments", json={"symbol": "TSLA", "kind": "STOCK", "currency": "EUR"})
    assert r.status_code == 409


def test_create_instrument_invalid_kind_returns_422(client):
    r = client.post("/instruments", json={"symbol": "XYZ", "kind": "INVALID", "currency": "EUR"})
    assert r.status_code == 422


def test_create_instrument_invalid_currency_returns_422(client):
    r = client.post("/instruments", json={"symbol": "XYZ", "kind": "STOCK", "currency": "ZZZ"})
    assert r.status_code == 422


def test_list_instruments(client):
    _create_instrument(client, "GOOG")
    _create_instrument(client, "AMZN")

    r = client.get("/instruments")
    assert r.status_code == 200
    symbols = [i["symbol"] for i in r.json()]
    assert "GOOG" in symbols
    assert "AMZN" in symbols


def test_list_instruments_empty(client):
    r = client.get("/instruments")
    assert r.status_code == 200
    assert r.json() == []


def test_delete_instrument(client):
    _create_instrument(client, "DEL_INST")

    r = client.delete("/instruments/DEL_INST")
    assert r.status_code == 204

    r2 = client.get("/instruments")
    symbols = [i["symbol"] for i in r2.json()]
    assert "DEL_INST" not in symbols


def test_delete_instrument_not_found_returns_404(client):
    r = client.delete("/instruments/GHOST")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

def test_list_prices_empty(client):
    r = client.get("/prices")
    assert r.status_code == 200
    assert r.json() == []


def test_latest_price_not_found_returns_404(client):
    r = client.get("/prices/GHOST/latest")
    assert r.status_code == 404


def test_list_prices_requires_symbol_for_date_filter(client):
    # date_from sans symbol => 422
    r = client.get("/prices", params={"date_from": "2026-01-01", "date_to": "2026-01-31"})
    assert r.status_code == 422


def test_list_prices_date_from_without_date_to_returns_422(client):
    r = client.get("/prices", params={"symbol": "AAPL", "date_from": "2026-01-01"})
    assert r.status_code == 422
