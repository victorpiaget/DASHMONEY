"""
Tests pour l'endpoint /accounts/{id}/budget-summary.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_account(client, account_id: str, *, currency="EUR"):
    r = client.post("/accounts", json={
        "id": account_id,
        "name": f"Account {account_id}",
        "currency": currency,
        "opening_balance": "0.00",
        "opened_on": "2026-01-01",
        "account_type": "CHECKING",
        "profile_id": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _add_tx(client, account_id, *, date, amount, kind, category, subcategory=None):
    r = client.post(f"/accounts/{account_id}/transactions", json={
        "date": date,
        "amount": amount,
        "kind": kind,
        "category": category,
        "subcategory": subcategory,
        "label": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_budget_summary_no_transactions(client):
    _create_account(client, "BUD1")

    r = client.get("/accounts/BUD1/budget-summary")
    assert r.status_code == 200
    data = r.json()

    assert data["account_id"] == "BUD1"
    assert data["currency"] == "EUR"
    assert data["totals_by_kind"] == []
    assert data["expense_by_category"] == []
    assert data["expense_by_subcategory"] == []
    assert data["monthly_by_kind"] == []


def test_budget_summary_totals_by_kind(client):
    _create_account(client, "BUD2")
    _add_tx(client, "BUD2", date="2026-01-10", amount="-50.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD2", date="2026-01-11", amount="-30.00", kind="EXPENSE", category="transport")
    _add_tx(client, "BUD2", date="2026-01-15", amount="200.00", kind="INCOME", category="salary")

    r = client.get("/accounts/BUD2/budget-summary")
    assert r.status_code == 200
    data = r.json()

    from decimal import Decimal
    kinds = {item["kind"]: Decimal(item["total"]) for item in data["totals_by_kind"]}
    assert "EXPENSE" in kinds
    assert "INCOME" in kinds
    assert abs(kinds["EXPENSE"]) == Decimal("80.00")
    assert kinds["INCOME"] == Decimal("200.00")


def test_budget_summary_expense_by_category(client):
    _create_account(client, "BUD3")
    _add_tx(client, "BUD3", date="2026-01-10", amount="-40.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD3", date="2026-01-11", amount="-25.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD3", date="2026-01-12", amount="-60.00", kind="EXPENSE", category="rent")

    r = client.get("/accounts/BUD3/budget-summary")
    assert r.status_code == 200
    data = r.json()

    from decimal import Decimal
    by_cat = {item["category"]: Decimal(item["total"]) for item in data["expense_by_category"]}
    assert abs(by_cat["food"]) == Decimal("65.00")
    assert abs(by_cat["rent"]) == Decimal("60.00")


def test_budget_summary_expense_by_subcategory(client):
    _create_account(client, "BUD4")
    _add_tx(client, "BUD4", date="2026-01-10", amount="-20.00", kind="EXPENSE",
            category="food", subcategory="groceries")
    _add_tx(client, "BUD4", date="2026-01-11", amount="-15.00", kind="EXPENSE",
            category="food", subcategory="restaurant")
    _add_tx(client, "BUD4", date="2026-01-12", amount="-10.00", kind="EXPENSE",
            category="food", subcategory="groceries")

    r = client.get("/accounts/BUD4/budget-summary")
    assert r.status_code == 200
    data = r.json()

    from decimal import Decimal
    by_sub = {
        (item["category"], item["subcategory"]): Decimal(item["total"])
        for item in data["expense_by_subcategory"]
    }
    assert abs(by_sub[("food", "groceries")]) == Decimal("30.00")
    assert abs(by_sub[("food", "restaurant")]) == Decimal("15.00")


def test_budget_summary_monthly_by_kind(client):
    _create_account(client, "BUD5")
    _add_tx(client, "BUD5", date="2026-01-10", amount="-50.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD5", date="2026-02-10", amount="-70.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD5", date="2026-01-15", amount="300.00", kind="INCOME", category="salary")

    r = client.get("/accounts/BUD5/budget-summary")
    assert r.status_code == 200
    data = r.json()

    from decimal import Decimal
    monthly = data["monthly_by_kind"]
    assert len(monthly) >= 3  # jan expense, jan income, feb expense

    jan_expense = next(
        (m for m in monthly if m["year"] == 2026 and m["month"] == 1 and m["kind"] == "EXPENSE"),
        None,
    )
    assert jan_expense is not None
    assert abs(Decimal(jan_expense["total"])) == Decimal("50.00")

    jan_income = next(
        (m for m in monthly if m["year"] == 2026 and m["month"] == 1 and m["kind"] == "INCOME"),
        None,
    )
    assert jan_income is not None
    assert Decimal(jan_income["total"]) == Decimal("300.00")


def test_budget_summary_date_filter(client):
    _create_account(client, "BUD6")
    _add_tx(client, "BUD6", date="2026-01-10", amount="-50.00", kind="EXPENSE", category="food")
    _add_tx(client, "BUD6", date="2026-03-10", amount="-100.00", kind="EXPENSE", category="food")

    # filtre sur janvier seulement
    r = client.get("/accounts/BUD6/budget-summary", params={
        "date_from": "2026-01-01",
        "date_to": "2026-01-31",
    })
    assert r.status_code == 200
    data = r.json()

    from decimal import Decimal
    kinds = {item["kind"]: Decimal(item["total"]) for item in data["totals_by_kind"]}
    # seulement la tx de janvier => 50 (pas 150)
    assert abs(kinds.get("EXPENSE", Decimal("0"))) == Decimal("50.00")


def test_budget_summary_account_not_found_returns_404(client):
    r = client.get("/accounts/GHOST_BUD/budget-summary")
    assert r.status_code == 404
