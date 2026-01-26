from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_create_and_list_transactions():
    # create
    payload = {
        "account_id": "main",
        "date": "2026-01-10",
        "amount": "1000",
        "currency": "EUR",
        "kind": "INCOME",
        "category": "Revenus",
        "subcategory": "Salaire",
        "label": "Stage",
    }

    r = client.post("/transactions", json=payload)
    assert r.status_code == 201, r.text
    created = r.json()

    assert created["sequence"] == 1
    assert created["amount"] == "1000.00"
    assert created["currency"] == "EUR"
    assert created["kind"] == "INCOME"

    # create second same day -> sequence increments
    payload2 = payload | {"amount": "-10", "kind": "EXPENSE", "category": "Dépenses", "subcategory": "Test"}
    r2 = client.post("/transactions", json=payload2)
    assert r2.status_code == 201, r2.text
    assert r2.json()["sequence"] == 2

    # list
    r3 = client.get("/transactions?account_id=main")
    assert r3.status_code == 200
    items = r3.json()
    assert len(items) >= 2
    assert [it["sequence"] for it in items[:2]] == [1, 2]
