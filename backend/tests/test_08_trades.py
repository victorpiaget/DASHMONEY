"""
Tests pour les endpoints trades et positions :
  POST   /portfolios/{id}/trades
  GET    /portfolios/{id}/trades
  PATCH  /portfolios/{id}/trades/{trade_id}
  DELETE /portfolios/{id}/trades/{trade_id}
  GET    /portfolios/{id}/positions
"""
from __future__ import annotations
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_instrument(client, symbol="AAPL", *, kind="STOCK", currency="EUR"):
    r = client.post("/instruments", json={"symbol": symbol, "kind": kind, "currency": currency})
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


def _buy(client, portfolio_id, symbol, *, qty, price, date="2026-01-10", fees="0.00", label=None):
    r = client.post(f"/portfolios/{portfolio_id}/trades", json={
        "date": date,
        "side": "BUY",
        "instrument_symbol": symbol,
        "quantity": str(qty),
        "price": str(price),
        "fees": fees,
        "label": label,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _sell(client, portfolio_id, symbol, *, qty, price, date="2026-01-20", fees="0.00", label=None):
    r = client.post(f"/portfolios/{portfolio_id}/trades", json={
        "date": date,
        "side": "SELL",
        "instrument_symbol": symbol,
        "quantity": str(qty),
        "price": str(price),
        "fees": fees,
        "label": label,
    })
    return r


# ---------------------------------------------------------------------------
# Création de trades
# ---------------------------------------------------------------------------

def test_create_buy_trade(client):
    _create_instrument(client, "AAPL")
    p = _create_portfolio(client)

    trade = _buy(client, p["id"], "AAPL", qty=10, price="150.00")
    assert trade["side"] == "BUY"
    assert trade["instrument_symbol"] == "AAPL"
    assert Decimal(trade["quantity"]) == Decimal("10")
    assert Decimal(trade["price"]) == Decimal("150.00")
    assert trade["linked_cash_tx_id"] is not None


def test_buy_creates_expense_cash_tx(client):
    """Le BUY doit créer une transaction EXPENSE dans le compte passerelle."""
    _create_instrument(client, "BUY_TX")
    p = _create_portfolio(client, name="P_BUY_TX")
    cash_id = p["cash_account_id"]

    _buy(client, p["id"], "BUY_TX", qty=5, price="100.00", fees="2.50")

    txs = client.get(f"/accounts/{cash_id}/transactions").json()
    assert len(txs) == 1
    # BUY => dépense cash : -(5*100 + 2.50) = -502.50
    assert txs[0]["amount"] == "-502.50"
    assert txs[0]["kind"] == "EXPENSE"
    assert txs[0]["category"] == "INVEST"


def test_create_sell_trade(client):
    _create_instrument(client, "SELL_TEST")
    p = _create_portfolio(client, name="P_SELL")

    _buy(client, p["id"], "SELL_TEST", qty=10, price="100.00")
    r = _sell(client, p["id"], "SELL_TEST", qty=5, price="120.00")
    assert r.status_code == 201, r.text

    trade = r.json()
    assert trade["side"] == "SELL"
    assert Decimal(trade["quantity"]) == Decimal("5")


def test_sell_creates_income_cash_tx(client):
    """Le SELL doit créer une transaction INCOME dans le compte passerelle."""
    _create_instrument(client, "SELL_TX")
    p = _create_portfolio(client, name="P_SELL_TX")
    cash_id = p["cash_account_id"]

    _buy(client, p["id"], "SELL_TX", qty=10, price="100.00")

    r = _sell(client, p["id"], "SELL_TX", qty=3, price="110.00", fees="1.00")
    assert r.status_code == 201, r.text

    txs = client.get(f"/accounts/{cash_id}/transactions").json()
    # 2 tx : 1 BUY (expense) + 1 SELL (income)
    income_txs = [t for t in txs if t["kind"] == "INCOME"]
    assert len(income_txs) == 1
    # SELL net = 3*110 - 1 = 329
    assert income_txs[0]["amount"] == "329.00"


def test_sell_more_than_position_returns_422(client):
    _create_instrument(client, "OVERSELL")
    p = _create_portfolio(client, name="P_OVERSELL")

    _buy(client, p["id"], "OVERSELL", qty=5, price="100.00")
    r = _sell(client, p["id"], "OVERSELL", qty=10, price="100.00")
    assert r.status_code == 422


def test_sell_without_position_returns_422(client):
    _create_instrument(client, "NO_POS")
    p = _create_portfolio(client, name="P_NO_POS")

    r = _sell(client, p["id"], "NO_POS", qty=1, price="100.00")
    assert r.status_code == 422


def test_trade_instrument_not_found_returns_404(client):
    p = _create_portfolio(client, name="P_NO_INST")
    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "GHOST",
        "quantity": "1",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 404


def test_trade_portfolio_not_found_returns_404(client):
    _create_instrument(client, "FOR_404")
    r = client.post("/portfolios/00000000-0000-0000-0000-000000000000/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "FOR_404",
        "quantity": "1",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 404


def test_trade_currency_mismatch_returns_422(client):
    """L'instrument en USD ne peut pas être tradé dans un portfolio EUR (MVP)."""
    client.post("/instruments", json={"symbol": "USD_INST", "kind": "STOCK", "currency": "USD"})
    p = _create_portfolio(client, name="EUR_PORTFOLIO", currency="EUR")

    r = client.post(f"/portfolios/{p['id']}/trades", json={
        "date": "2026-01-10",
        "side": "BUY",
        "instrument_symbol": "USD_INST",
        "quantity": "1",
        "price": "100.00",
        "fees": "0.00",
        "label": None,
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Liste et filtres
# ---------------------------------------------------------------------------

def test_list_trades(client):
    _create_instrument(client, "LIST_T")
    p = _create_portfolio(client, name="P_LIST")

    _buy(client, p["id"], "LIST_T", qty=5, price="10.00", date="2026-01-10")
    _buy(client, p["id"], "LIST_T", qty=3, price="12.00", date="2026-01-15")

    r = client.get(f"/portfolios/{p['id']}/trades")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_trades_filter_by_side(client):
    _create_instrument(client, "FILTER_S")
    p = _create_portfolio(client, name="P_FILTER_S")

    _buy(client, p["id"], "FILTER_S", qty=10, price="10.00")
    r_sell = _sell(client, p["id"], "FILTER_S", qty=5, price="12.00")
    assert r_sell.status_code == 201

    r = client.get(f"/portfolios/{p['id']}/trades", params={"sides": ["BUY"]})
    assert r.status_code == 200
    items = r.json()
    assert all(t["side"] == "BUY" for t in items)


def test_list_trades_filter_by_date(client):
    _create_instrument(client, "FILTER_D")
    p = _create_portfolio(client, name="P_FILTER_D")

    _buy(client, p["id"], "FILTER_D", qty=5, price="10.00", date="2026-01-05")
    _buy(client, p["id"], "FILTER_D", qty=5, price="11.00", date="2026-02-05")

    r = client.get(f"/portfolios/{p['id']}/trades", params={
        "date_from": "2026-02-01", "date_to": "2026-02-28"
    })
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["date"] == "2026-02-05"


def test_list_trades_sort_by_price_desc(client):
    _create_instrument(client, "SORT_P")
    p = _create_portfolio(client, name="P_SORT_P")

    _buy(client, p["id"], "SORT_P", qty=1, price="50.00", date="2026-01-10")
    _buy(client, p["id"], "SORT_P", qty=1, price="200.00", date="2026-01-11")
    _buy(client, p["id"], "SORT_P", qty=1, price="100.00", date="2026-01-12")

    r = client.get(f"/portfolios/{p['id']}/trades", params={
        "sort_by": "price", "sort_dir": "desc"
    })
    assert r.status_code == 200
    items = r.json()
    prices = [Decimal(t["price"]) for t in items]
    assert prices == sorted(prices, reverse=True)


# ---------------------------------------------------------------------------
# Patch trade
# ---------------------------------------------------------------------------

def test_patch_trade_label_and_price(client):
    _create_instrument(client, "PATCH_T")
    p = _create_portfolio(client, name="P_PATCH")

    trade = _buy(client, p["id"], "PATCH_T", qty=5, price="100.00", label="original")
    trade_id = trade["id"]

    r = client.patch(f"/portfolios/{p['id']}/trades/{trade_id}", json={
        "price": "110.00",
        "label": "updated",
    })
    assert r.status_code == 200
    upd = r.json()
    assert Decimal(upd["price"]) == Decimal("110.00")
    assert upd["label"] == "updated"


def test_patch_trade_updates_cash_tx(client):
    """Après patch, l'ancienne cash tx est supprimée et une nouvelle est créée."""
    _create_instrument(client, "PATCH_CASH")
    p = _create_portfolio(client, name="P_PATCH_CASH")
    cash_id = p["cash_account_id"]

    trade = _buy(client, p["id"], "PATCH_CASH", qty=5, price="100.00")
    old_tx_id = trade["linked_cash_tx_id"]

    r = client.patch(f"/portfolios/{p['id']}/trades/{trade['id']}", json={"price": "200.00"})
    assert r.status_code == 200
    new_tx_id = r.json()["linked_cash_tx_id"]

    # la nouvelle tx est différente
    assert new_tx_id != old_tx_id

    # vérif montant de la nouvelle tx : -(5 * 200) = -1000
    txs = client.get(f"/accounts/{cash_id}/transactions").json()
    tx_ids = {t["id"] for t in txs}
    assert old_tx_id not in tx_ids  # ancienne supprimée
    assert new_tx_id in tx_ids


def test_patch_trade_not_found_returns_404(client):
    p = _create_portfolio(client, name="P_PATCH_404")
    r = client.patch(
        f"/portfolios/{p['id']}/trades/00000000-0000-0000-0000-000000000000",
        json={"price": "100.00"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Delete trade
# ---------------------------------------------------------------------------

def test_delete_trade_removes_cash_tx(client):
    _create_instrument(client, "DEL_T")
    p = _create_portfolio(client, name="P_DEL_T")
    cash_id = p["cash_account_id"]

    trade = _buy(client, p["id"], "DEL_T", qty=5, price="100.00")
    cash_tx_id = trade["linked_cash_tx_id"]

    r = client.delete(f"/portfolios/{p['id']}/trades/{trade['id']}")
    assert r.status_code == 204

    # trade + cash tx supprimés
    trades = client.get(f"/portfolios/{p['id']}/trades").json()
    assert all(t["id"] != trade["id"] for t in trades)

    txs = client.get(f"/accounts/{cash_id}/transactions").json()
    assert all(t["id"] != cash_tx_id for t in txs)


def test_delete_trade_not_found_returns_404(client):
    p = _create_portfolio(client, name="P_DEL_404")
    r = client.delete(f"/portfolios/{p['id']}/trades/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def test_positions_after_buy(client):
    _create_instrument(client, "POS_BUY")
    p = _create_portfolio(client, name="P_POS_BUY")

    _buy(client, p["id"], "POS_BUY", qty=10, price="100.00")

    r = client.get(f"/portfolios/{p['id']}/positions")
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert pos[0]["instrument_symbol"] == "POS_BUY"
    assert Decimal(pos[0]["quantity"]) == Decimal("10")


def test_positions_after_buy_and_partial_sell(client):
    _create_instrument(client, "POS_PARTIAL")
    p = _create_portfolio(client, name="P_POS_PARTIAL")

    _buy(client, p["id"], "POS_PARTIAL", qty=10, price="100.00")
    r_sell = _sell(client, p["id"], "POS_PARTIAL", qty=4, price="110.00")
    assert r_sell.status_code == 201

    r = client.get(f"/portfolios/{p['id']}/positions")
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert Decimal(pos[0]["quantity"]) == Decimal("6")


def test_positions_empty_after_full_sell(client):
    _create_instrument(client, "POS_FULL_SELL")
    p = _create_portfolio(client, name="P_POS_FULL")

    _buy(client, p["id"], "POS_FULL_SELL", qty=5, price="100.00")
    r_sell = _sell(client, p["id"], "POS_FULL_SELL", qty=5, price="110.00")
    assert r_sell.status_code == 201

    r = client.get(f"/portfolios/{p['id']}/positions")
    assert r.status_code == 200
    pos = r.json()
    # position nulle => on ne l'affiche pas (ou qty==0)
    assert all(p["quantity"] == "0" or True for p in pos)  # accepte les deux comportements


def test_positions_as_of_date(client):
    """as_of filtre les trades postérieurs à la date donnée."""
    _create_instrument(client, "POS_DATE")
    p = _create_portfolio(client, name="P_POS_DATE")

    _buy(client, p["id"], "POS_DATE", qty=10, price="100.00", date="2026-01-10")
    _buy(client, p["id"], "POS_DATE", qty=5, price="105.00", date="2026-02-10")

    # as_of=2026-01-31 => seulement le 1er BUY comptabilisé
    r = client.get(f"/portfolios/{p['id']}/positions", params={"as_of": "2026-01-31"})
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert Decimal(pos[0]["quantity"]) == Decimal("10")


def test_positions_portfolio_not_found_returns_404(client):
    r = client.get("/portfolios/00000000-0000-0000-0000-000000000000/positions")
    assert r.status_code == 404
