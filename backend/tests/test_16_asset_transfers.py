"""
Tests pour /asset-transfers :
  POST   /asset-transfers
  GET    /asset-transfers
  DELETE /asset-transfers/{sell_trade_id}
"""
from __future__ import annotations

from decimal import Decimal


def _create_instrument(client, symbol="BTC", *, kind="CRYPTO", currency="EUR"):
    r = client.post("/instruments", json={"symbol": symbol, "kind": kind, "currency": currency})
    assert r.status_code == 201, r.text
    return r.json()


def _create_portfolio(client, *, name="PEA", currency="EUR"):
    r = client.post("/portfolios", json={
        "name": name,
        "currency": currency,
        "portfolio_type": "CTO",
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


def _transfer(client, from_id, to_id, symbol, *, qty, date="2026-01-15", fees=None):
    payload = {
        "from_portfolio_id": from_id,
        "to_portfolio_id": to_id,
        "instrument_symbol": symbol,
        "quantity": str(qty),
        "date": date,
    }
    if fees is not None:
        payload["fees"] = str(fees)
    return client.post("/asset-transfers", json=payload)


def test_create_asset_transfer_creates_two_trades(client):
    _create_instrument(client, "BTC_T1")
    p1 = _create_portfolio(client, name="Source")
    p2 = _create_portfolio(client, name="Dest")

    _buy(client, p1["id"], "BTC_T1", qty=5, price="100.00")

    r = _transfer(client, p1["id"], p2["id"], "BTC_T1", qty=3)
    assert r.status_code == 201, r.text
    data = r.json()
    assert "sell" in data
    assert "buy" in data
    assert data["sell"]["trade_type"] == "TRANSFER"
    assert data["buy"]["trade_type"] == "TRANSFER"

    pos1 = {p["instrument_symbol"]: Decimal(p["quantity"])
            for p in client.get(f"/portfolios/{p1['id']}/positions").json()}
    pos2 = {p["instrument_symbol"]: Decimal(p["quantity"])
            for p in client.get(f"/portfolios/{p2['id']}/positions").json()}

    assert pos1.get("BTC_T1", Decimal("0")) == Decimal("2")
    assert pos2.get("BTC_T1", Decimal("0")) == Decimal("3")


def test_asset_transfer_excluded_from_pnl(client):
    _create_instrument(client, "BTC_PNL")
    p1 = _create_portfolio(client, name="SrcPNL")
    p2 = _create_portfolio(client, name="DstPNL")
    cash1_id = p1["cash_account_id"]

    _buy(client, p1["id"], "BTC_PNL", qty=10, price="50.00")

    r = _transfer(client, p1["id"], p2["id"], "BTC_PNL", qty=5)
    assert r.status_code == 201, r.text

    txs = client.get(f"/accounts/{cash1_id}/transactions").json()
    assert len(txs) == 1, f"Expected 1 cash tx (BUY only), got {len(txs)}: {txs}"
    assert txs[0]["kind"] == "EXPENSE"


def test_asset_transfer_same_portfolio_returns_422(client):
    _create_instrument(client, "BTC_SAME")
    p = _create_portfolio(client, name="SinglePortfolio")
    _buy(client, p["id"], "BTC_SAME", qty=5)

    r = _transfer(client, p["id"], p["id"], "BTC_SAME", qty=3)
    assert r.status_code == 422, r.text


def test_asset_transfer_source_not_found_returns_404(client):
    _create_instrument(client, "BTC_404S")
    p2 = _create_portfolio(client, name="DstOnly")

    r = _transfer(client, "00000000-0000-0000-0000-000000000000", p2["id"], "BTC_404S", qty=1)
    assert r.status_code == 404, r.text


def test_asset_transfer_destination_not_found_returns_404(client):
    _create_instrument(client, "BTC_404D")
    p1 = _create_portfolio(client, name="SrcOnly")
    _buy(client, p1["id"], "BTC_404D", qty=5)

    r = _transfer(client, p1["id"], "00000000-0000-0000-0000-000000000000", "BTC_404D", qty=1)
    assert r.status_code == 404, r.text


def test_asset_transfer_instrument_not_found_returns_404(client):
    p1 = _create_portfolio(client, name="SrcInst")
    p2 = _create_portfolio(client, name="DstInst")

    r = _transfer(client, p1["id"], p2["id"], "GHOST_INSTRUMENT", qty=1)
    assert r.status_code == 404, r.text


def test_asset_transfer_insufficient_quantity_returns_422(client):
    _create_instrument(client, "BTC_INSUF")
    p1 = _create_portfolio(client, name="SrcInsuf")
    p2 = _create_portfolio(client, name="DstInsuf")

    r = client.post("/asset-transfers", json={
        "from_portfolio_id": p1["id"],
        "to_portfolio_id": p2["id"],
        "instrument_symbol": "BTC_INSUF",
        "quantity": "-1",
        "date": "2026-01-15",
    })
    assert r.status_code == 422, r.text


def test_list_asset_transfers(client):
    _create_instrument(client, "BTC_LIST")
    p1 = _create_portfolio(client, name="SrcList")
    p2 = _create_portfolio(client, name="DstList")

    _buy(client, p1["id"], "BTC_LIST", qty=10)
    r1 = _transfer(client, p1["id"], p2["id"], "BTC_LIST", qty=3)
    assert r1.status_code == 201, r1.text
    r2 = _transfer(client, p1["id"], p2["id"], "BTC_LIST", qty=2, date="2026-01-20")
    assert r2.status_code == 201, r2.text

    r = client.get("/asset-transfers")
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 2
    for item in items:
        assert "sell_trade_id" in item
        assert item["instrument_symbol"] == "BTC_LIST"


def test_delete_asset_transfer_restores_positions(client):
    _create_instrument(client, "BTC_DEL")
    p1 = _create_portfolio(client, name="SrcDel")
    p2 = _create_portfolio(client, name="DstDel")

    _buy(client, p1["id"], "BTC_DEL", qty=5)
    r = _transfer(client, p1["id"], p2["id"], "BTC_DEL", qty=3)
    assert r.status_code == 201, r.text
    sell_trade_id = r.json()["sell"]["id"]

    pos2_before = {p["instrument_symbol"]: Decimal(p["quantity"])
                   for p in client.get(f"/portfolios/{p2['id']}/positions").json()}
    assert pos2_before.get("BTC_DEL", Decimal("0")) == Decimal("3")

    del_r = client.delete(f"/asset-transfers/{sell_trade_id}")
    assert del_r.status_code == 204, del_r.text

    pos1_after = {p["instrument_symbol"]: Decimal(p["quantity"])
                  for p in client.get(f"/portfolios/{p1['id']}/positions").json()}
    pos2_after = {p["instrument_symbol"]: Decimal(p["quantity"])
                  for p in client.get(f"/portfolios/{p2['id']}/positions").json()}

    assert pos1_after.get("BTC_DEL", Decimal("0")) == Decimal("5")
    assert pos2_after.get("BTC_DEL", Decimal("0")) == Decimal("0")


def test_delete_nonexistent_asset_transfer_returns_404(client):
    r = client.delete("/asset-transfers/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404, r.text
