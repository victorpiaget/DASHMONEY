def _create_account(client, account_id: str = "ACC_TX", *, currency="EUR"):
    payload = {
        "id": account_id,
        "name": "Account for TX",
        "currency": currency,
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }
    r = client.post("/accounts", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list_transactions(client):
    _create_account(client, "ACC_TX_1")

    payload = {
        "date": "2026-01-10",
        "amount": "-12.34",
        "kind": "EXPENSE",
        "category": "food",
        "subcategory": "groceries",
        "label": "Carrefour",
    }
    r = client.post("/accounts/ACC_TX_1/transactions", json=payload)
    assert r.status_code == 201, r.text
    tx = r.json()
    assert tx["account_id"] == "ACC_TX_1"
    assert tx["amount"] == "-12.34"
    assert tx["kind"] == "EXPENSE"
    assert tx["category"] == "food"

    r2 = client.get("/accounts/ACC_TX_1/transactions")
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert len(items) == 1
    assert items[0]["id"] == tx["id"]


def test_filters_kinds_and_q(client):
    _create_account(client, "ACC_TX_2")

    # expense
    r1 = client.post(
        "/accounts/ACC_TX_2/transactions",
        json={
            "date": "2026-01-10",
            "amount": "-20.00",
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "pizza",
        },
    )
    assert r1.status_code == 201, r1.text

    # income
    r2 = client.post(
        "/accounts/ACC_TX_2/transactions",
        json={
            "date": "2026-01-11",
            "amount": "100.00",
            "kind": "INCOME",
            "category": "salary",
            "subcategory": None,
            "label": "January",
        },
    )
    assert r2.status_code == 201, r2.text

    # filter by kind
    r_k = client.get("/accounts/ACC_TX_2/transactions", params={"kinds": ["INCOME"]})
    assert r_k.status_code == 200, r_k.text
    items = r_k.json()
    assert len(items) == 1
    assert items[0]["kind"] == "INCOME"

    # search by q (label)
    r_q = client.get("/accounts/ACC_TX_2/transactions", params={"q": "pizza"})
    assert r_q.status_code == 200, r_q.text
    items = r_q.json()
    assert len(items) == 1
    assert "pizza" in (items[0].get("label") or "").lower()


def test_sort_by_amount_desc(client):
    _create_account(client, "ACC_TX_3")

    # -5
    r1 = client.post(
        "/accounts/ACC_TX_3/transactions",
        json={
            "date": "2026-01-10",
            "amount": "-5.00",
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "small",
        },
    )
    assert r1.status_code == 201, r1.text

    # -30
    r2 = client.post(
        "/accounts/ACC_TX_3/transactions",
        json={
            "date": "2026-01-10",
            "amount": "-30.00",
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "big",
        },
    )
    assert r2.status_code == 201, r2.text

    r = client.get(
        "/accounts/ACC_TX_3/transactions",
        params={"sort_by": "amount", "sort_dir": "desc"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 2

    # desc by amount: -5.00 should come before -30.00
    assert items[0]["amount"] == "-5.00"
    assert items[1]["amount"] == "-30.00"


def test_update_transaction(client):
    _create_account(client, "ACC_TX_4")

    r = client.post(
        "/accounts/ACC_TX_4/transactions",
        json={
            "date": "2026-01-10",
            "amount": "-10.00",
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "old",
        },
    )
    assert r.status_code == 201, r.text
    tx_id = r.json()["id"]

    # patch label + category
    r2 = client.patch(
        f"/accounts/ACC_TX_4/transactions/{tx_id}",
        json={"label": "new", "category": "restaurants"},
    )
    assert r2.status_code == 200, r2.text
    upd = r2.json()
    assert upd["id"] == tx_id
    assert upd["label"] == "new"
    assert upd["category"] == "restaurants"


def test_delete_transaction(client):
    _create_account(client, "ACC_TX_5")

    r = client.post(
        "/accounts/ACC_TX_5/transactions",
        json={
            "date": "2026-01-10",
            "amount": "-10.00",
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "to delete",
        },
    )
    assert r.status_code == 201, r.text
    tx_id = r.json()["id"]

    r2 = client.delete(f"/accounts/ACC_TX_5/transactions/{tx_id}")
    assert r2.status_code == 204, r2.text

    r3 = client.get("/accounts/ACC_TX_5/transactions")
    assert r3.status_code == 200, r3.text
    assert r3.json() == []


def test_invalid_amount_returns_422(client):
    _create_account(client, "ACC_TX_6")

    r = client.post(
        "/accounts/ACC_TX_6/transactions",
        json={
            "date": "2026-01-10",
            "amount": "12.345",  # invalid (more than 2 decimals)
            "kind": "EXPENSE",
            "category": "food",
            "subcategory": None,
            "label": "bad",
        },
    )
    assert r.status_code == 422, r.text


def test_delete_nonexistent_tx_returns_404_or_422(client):
    _create_account(client, "ACC_TX_7")

    r = client.delete("/accounts/ACC_TX_7/transactions/does-not-exist")
    # depending on your repo behavior this can be 404 (preferred) or 422 if id validation fails
    assert r.status_code in (404, 422), r.text