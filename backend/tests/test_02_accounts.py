from app.identity.defaults import DEFAULT_PROFILE_ID, DEFAULT_WORKSPACE_ID


def test_create_account_in_default_profile_and_list(client):
    payload = {
        "id": "ACC_A",
        "name": "Account A",
        "currency": "EUR",
        "opening_balance": "100.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }

    r = client.post("/accounts", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["id"] == "ACC_A"
    assert created["currency"] == "EUR"

    # list without profile_id => default profile scope
    r2 = client.get("/accounts")
    assert r2.status_code == 200
    ids = [a["id"] for a in r2.json()]
    assert "ACC_A" in ids


def test_accounts_are_isolated_by_profile_id(client):
    # create a new profile
    pr = client.post(
        f"/workspaces/{DEFAULT_WORKSPACE_ID}/profiles",
        json={"display_name": "QA Other Profile"},
    )
    assert pr.status_code == 201
    other_profile_id = pr.json()["id"]
    assert other_profile_id != DEFAULT_PROFILE_ID

    # create account in other profile explicitly
    payload = {
        "id": "ACC_B",
        "name": "Account B",
        "currency": "EUR",
        "opening_balance": "50.00",
        "opened_on": "2026-01-02",
        "account_type": "CHECKING",
    }
    r = client.post("/accounts", json=payload, params={"profile_id": other_profile_id})
    assert r.status_code == 201

    # list in default profile => must NOT include ACC_B
    r_default = client.get("/accounts")
    assert r_default.status_code == 200
    ids_default = [a["id"] for a in r_default.json()]
    assert "ACC_B" not in ids_default

    # list in other profile => must include ACC_B
    r_other = client.get("/accounts", params={"profile_id": other_profile_id})
    assert r_other.status_code == 200
    ids_other = [a["id"] for a in r_other.json()]
    assert "ACC_B" in ids_other


def test_get_account_balance(client):
    # create account
    payload = {
        "id": "ACC_BAL",
        "name": "Account Balance",
        "currency": "EUR",
        "opening_balance": "123.45",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }
    r = client.post("/accounts", json=payload)
    assert r.status_code == 201

    # balance at opening date => should match opening_balance (no tx yet)
    r2 = client.get("/accounts/ACC_BAL/balance", params={"at": "2026-01-01"})
    assert r2.status_code == 200
    bal = r2.json()

    assert bal["account_id"] == "ACC_BAL"
    assert bal["currency"] == "EUR"
    assert bal["balance"] == "123.45"


def test_update_account_name(client):
    # create account
    payload = {
        "id": "ACC_UPD",
        "name": "Old Name",
        "currency": "EUR",
        "opening_balance": "10.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }
    r = client.post("/accounts", json=payload)
    assert r.status_code == 201

    # update
    r2 = client.patch("/accounts/ACC_UPD", json={"name": "New Name"})
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["id"] == "ACC_UPD"
    assert updated["name"] == "New Name"


def test_delete_account(client):
    # create account
    payload = {
        "id": "ACC_DEL",
        "name": "To delete",
        "currency": "EUR",
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    }
    r = client.post("/accounts", json=payload)
    assert r.status_code == 201

    # delete
    r2 = client.delete("/accounts/ACC_DEL")
    assert r2.status_code == 204

    # list => should not be present
    r3 = client.get("/accounts")
    assert r3.status_code == 200
    ids = [a["id"] for a in r3.json()]
    assert "ACC_DEL" not in ids