"""
Tests pour l'endpoint d'import CSV :
  POST /accounts/{id}/import-transactions-csv
"""
from __future__ import annotations

import io


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_account(client, account_id: str):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": "EUR",
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _upload_csv(client, account_id, csv_content: str, filename="transactions.csv"):
    return client.post(
        f"/accounts/{account_id}/import-transactions-csv",
        files={"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_import_csv_valid_file(client):
    _create_account(client, "IMP1")

    csv_content = (
        "date,kind,amount,category,subcategory,label\n"
        "2026-01-10,EXPENSE,-50.00,food,groceries,Carrefour\n"
        "2026-01-11,INCOME,200.00,salary,,Janvier\n"
        "2026-01-12,EXPENSE,-20.00,transport,,Bus\n"
    )

    r = _upload_csv(client, "IMP1", csv_content)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["imported"] == 3
    assert data["errors_count"] == 0

    # vérifier que les transactions sont bien en base
    txs = client.get("/accounts/IMP1/transactions").json()
    assert len(txs) == 3


def test_import_csv_partial_errors(client):
    _create_account(client, "IMP2")

    csv_content = (
        "date,kind,amount,category,subcategory,label\n"
        "2026-01-10,EXPENSE,-50.00,food,,Good line\n"
        "NOT_A_DATE,EXPENSE,-10.00,food,,Bad date\n"      # date invalide
        "2026-01-12,INVALID_KIND,-20.00,food,,Bad kind\n"  # kind invalide
        "2026-01-15,INCOME,100.00,salary,,Good again\n"
    )

    r = _upload_csv(client, "IMP2", csv_content)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["imported"] == 2
    assert data["errors_count"] == 2
    assert len(data["errors_preview"]) == 2


def test_import_csv_wrong_file_type_returns_422(client):
    _create_account(client, "IMP3")

    r = client.post(
        "/accounts/IMP3/import-transactions-csv",
        files={"file": ("transactions.txt", io.BytesIO(b"some content"), "text/plain")},
    )
    assert r.status_code == 422


def test_import_csv_missing_required_headers_returns_422(client):
    _create_account(client, "IMP4")

    # CSV sans colonne "kind"
    csv_content = "date,amount,category\n2026-01-10,-50.00,food\n"
    r = _upload_csv(client, "IMP4", csv_content)
    assert r.status_code == 422


def test_import_csv_account_not_found_returns_404(client):
    csv_content = (
        "date,kind,amount,category,subcategory,label\n"
        "2026-01-10,EXPENSE,-50.00,food,,test\n"
    )
    r = _upload_csv(client, "GHOST_IMP", csv_content)
    assert r.status_code == 404


def test_import_csv_empty_file(client):
    _create_account(client, "IMP5")

    # CSV avec header mais aucune ligne de données
    csv_content = "date,kind,amount,category,subcategory,label\n"
    r = _upload_csv(client, "IMP5", csv_content)
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 0
    assert data["errors_count"] == 0


def test_import_csv_creates_transactions_in_order(client):
    _create_account(client, "IMP6")

    csv_content = (
        "date,kind,amount,category,subcategory,label\n"
        "2026-01-15,EXPENSE,-30.00,food,,A\n"
        "2026-01-10,EXPENSE,-20.00,food,,B\n"
    )

    r = _upload_csv(client, "IMP6", csv_content)
    assert r.status_code == 200
    assert r.json()["imported"] == 2

    txs = client.get("/accounts/IMP6/transactions", params={"sort_by": "date", "sort_dir": "asc"}).json()
    assert len(txs) == 2
    assert txs[0]["date"] == "2026-01-10"
    assert txs[1]["date"] == "2026-01-15"


def test_import_csv_with_bom(client):
    """Support du BOM UTF-8 (export Excel)."""
    _create_account(client, "IMP7")

    # BOM + CSV valide
    csv_content = "\ufeffdate,kind,amount,category,subcategory,label\n2026-01-10,EXPENSE,-10.00,food,,test\n"
    r = _upload_csv(client, "IMP7", csv_content)
    assert r.status_code == 200
    assert r.json()["imported"] == 1
