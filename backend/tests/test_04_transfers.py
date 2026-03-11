def _create_account(client, account_id: str, *, currency="EUR", opening="0.00"):
    payload = {
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": currency,
        "opening_balance": opening,
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }
    r = client.post("/accounts", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_transfer_creates_two_legs(client):
    _create_account(client, "A", currency="EUR", opening="0.00")
    _create_account(client, "B", currency="EUR", opening="0.00")

    payload = {
        "to_account_id": "B",
        "date": "2026-01-11",
        "amount": "30.00",
        "category": "transfer",
        "subcategory": None,
        "label": "A->B",
    }
    r = client.post("/accounts/A/transfers", json=payload)
    assert r.status_code == 201, r.text
    tr = r.json()

    assert "transfer_id" in tr
    transfer_id = tr["transfer_id"]

    # verify both accounts have exactly one tx each
    ra = client.get("/accounts/A/transactions", params={"kinds": ["TRANSFER"]})
    assert ra.status_code == 200, ra.text
    ta = ra.json()
    assert len(ta) == 1
    assert ta[0]["transfer_id"] == transfer_id
    assert ta[0]["amount"] == "-30.00"

    rb = client.get("/accounts/B/transactions", params={"kinds": ["TRANSFER"]})
    assert rb.status_code == 200, rb.text
    tb = rb.json()
    assert len(tb) == 1
    assert tb[0]["transfer_id"] == transfer_id
    assert tb[0]["amount"] == "30.00"

    # balance impact check
    bal_a = client.get("/accounts/A/balance").json()
    bal_b = client.get("/accounts/B/balance").json()
    assert bal_a["balance"] == "-30.00"
    assert bal_b["balance"] == "30.00"


def test_update_transfer_updates_both_legs(client):
    _create_account(client, "A2", currency="EUR", opening="0.00")
    _create_account(client, "B2", currency="EUR", opening="0.00")

    r = client.post(
        "/accounts/A2/transfers",
        json={
            "to_account_id": "B2",
            "date": "2026-01-11",
            "amount": "10.00",
            "category": "transfer",
            "subcategory": None,
            "label": "init",
        },
    )
    assert r.status_code == 201, r.text
    transfer_id = r.json()["transfer_id"]

    # update amount + label + date
    r2 = client.patch(
        f"/accounts/A2/transfers/{transfer_id}",
        json={"amount": "12.50", "label": "updated", "date": "2026-01-12"},
    )
    assert r2.status_code == 200, r2.text

    # verify both legs reflect the update
    ta = client.get("/accounts/A2/transactions", params={"kinds": ["TRANSFER"]}).json()
    tb = client.get("/accounts/B2/transactions", params={"kinds": ["TRANSFER"]}).json()
    assert len(ta) == 1 and len(tb) == 1

    assert ta[0]["transfer_id"] == transfer_id
    assert tb[0]["transfer_id"] == transfer_id

    assert ta[0]["amount"] == "-12.50"
    assert tb[0]["amount"] == "12.50"

    assert ta[0]["label"] == "updated"
    assert tb[0]["label"] == "updated"

    assert ta[0]["date"] == "2026-01-12"
    assert tb[0]["date"] == "2026-01-12"


def test_delete_transfer_deletes_both_legs(client):
    _create_account(client, "A3", currency="EUR", opening="0.00")
    _create_account(client, "B3", currency="EUR", opening="0.00")

    r = client.post(
        "/accounts/A3/transfers",
        json={
            "to_account_id": "B3",
            "date": "2026-01-11",
            "amount": "5.00",
            "category": "transfer",
            "subcategory": None,
            "label": "to-delete",
        },
    )
    assert r.status_code == 201, r.text
    transfer_id = r.json()["transfer_id"]

    r2 = client.delete(f"/accounts/A3/transfers/{transfer_id}")
    assert r2.status_code == 204, r2.text

    ta = client.get("/accounts/A3/transactions", params={"kinds": ["TRANSFER"]}).json()
    tb = client.get("/accounts/B3/transactions", params={"kinds": ["TRANSFER"]}).json()
    assert ta == []
    assert tb == []


def test_transfer_currency_mismatch_returns_422(client):
    _create_account(client, "A4", currency="EUR", opening="0.00")
    _create_account(client, "B4", currency="USD", opening="0.00")

    r = client.post(
        "/accounts/A4/transfers",
        json={
            "to_account_id": "B4",
            "date": "2026-01-11",
            "amount": "10.00",
            "category": "transfer",
            "subcategory": None,
            "label": "mismatch",
        },
    )
    assert r.status_code == 422, r.text