"""Tests budget prévisionnel — engine (unitaires) + API (intégration)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.budget_envelope import BudgetEnvelope
from app.domain.money import Currency, Money
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.engine.budget import BudgetComparison, budget_synthesis, budget_vs_actual
from app.identity.defaults import DEFAULT_PROFILE_ID, DEFAULT_PROFILE2_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EUR = Currency.EUR


def _make_tx(
    *,
    category: str,
    subcategory: str | None = None,
    kind: TransactionKind,
    amount_str: str,
    date: dt.date = dt.date(2026, 3, 15),
) -> Transaction:
    return Transaction.create(
        account_id="acc-1",
        date=date,
        sequence=1,
        amount=SignedMoney.from_str(amount_str, EUR),
        kind=kind,
        category=category,
        subcategory=subcategory,
    )


def _make_env(
    *,
    category: str,
    subcategory: str | None = None,
    kind: TransactionKind,
    amount_str: str,
) -> BudgetEnvelope:
    return BudgetEnvelope.create(
        category=category,
        subcategory=subcategory,
        kind=kind,
        amount=Money.from_str(amount_str, EUR),
    )


# ---------------------------------------------------------------------------
# Tests engine — unitaires
# ---------------------------------------------------------------------------

class TestBudgetVsActual:

    def test_nominal_matched(self):
        env = _make_env(category="Revenus", kind=TransactionKind.INCOME, amount_str="3000.00")
        tx = _make_tx(category="Revenus", kind=TransactionKind.INCOME, amount_str="2800.00")

        result = budget_vs_actual([env], [tx], currency=EUR)
        assert len(result) == 1
        c = result[0]
        assert c.planned.amount == Decimal("3000.00")
        assert c.actual.amount == Decimal("2800.00")
        assert c.delta.amount == Decimal("-200.00")
        assert c.percent == Decimal("93.33")

    def test_transaction_without_envelope(self):
        tx = _make_tx(category="Restaurant", kind=TransactionKind.EXPENSE, amount_str="-150.00")

        result = budget_vs_actual([], [tx], currency=EUR)
        assert len(result) == 1
        c = result[0]
        assert c.planned.amount == Decimal("0.00")
        assert c.actual.amount == Decimal("-150.00")
        assert c.percent == Decimal("100.00")

    def test_envelope_without_transaction(self):
        env = _make_env(category="Logement", kind=TransactionKind.EXPENSE, amount_str="900.00")

        result = budget_vs_actual([env], [], currency=EUR)
        assert len(result) == 1
        c = result[0]
        assert c.actual.amount == Decimal("0.00")
        assert c.percent == Decimal("0.00")

    def test_with_subcategories(self):
        env_cat = _make_env(category="Revenus", kind=TransactionKind.INCOME, amount_str="3000.00")
        env_sub = _make_env(category="Revenus", subcategory="Salaire", kind=TransactionKind.INCOME, amount_str="2500.00")
        tx = _make_tx(category="Revenus", subcategory="Salaire", kind=TransactionKind.INCOME, amount_str="2500.00")

        result = budget_vs_actual([env_cat, env_sub], [tx], currency=EUR)
        # env_cat n'a pas de transaction matchant (cat only, no sub)
        cat_items = [r for r in result if r.subcategory is None]
        sub_items = [r for r in result if r.subcategory == "Salaire"]
        assert len(cat_items) == 1
        assert cat_items[0].actual.amount == Decimal("0.00")
        assert len(sub_items) == 1
        assert sub_items[0].actual.amount == Decimal("2500.00")

    def test_transfer_excluded(self):
        env = _make_env(category="Revenus", kind=TransactionKind.INCOME, amount_str="3000.00")
        transfer = Transaction.create(
            account_id="acc-1",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert interne",
        )

        result = budget_vs_actual([env], [transfer], currency=EUR)
        # transfer ignoré, env avec actual=0
        assert len(result) == 1
        assert result[0].actual.amount == Decimal("0.00")

    def test_expense_overspent(self):
        env = _make_env(category="Vie quotidienne", kind=TransactionKind.EXPENSE, amount_str="500.00")
        tx = _make_tx(category="Vie quotidienne", kind=TransactionKind.EXPENSE, amount_str="-650.00")

        result = budget_vs_actual([env], [tx], currency=EUR)
        assert len(result) == 1
        c = result[0]
        # delta positif = dépassement pour les dépenses
        assert c.delta.amount == Decimal("150.00")
        assert c.percent == Decimal("130.00")


class TestBudgetSynthesis:

    def test_nominal(self):
        comparisons = [
            BudgetComparison(
                category="Revenus", subcategory=None, kind=TransactionKind.INCOME,
                planned=Money.from_str("3000.00", EUR),
                actual=SignedMoney.from_str("2800.00", EUR),
                delta=SignedMoney.from_str("-200.00", EUR),
                percent=Decimal("93.33"),
            ),
            BudgetComparison(
                category="Logement", subcategory=None, kind=TransactionKind.EXPENSE,
                planned=Money.from_str("900.00", EUR),
                actual=SignedMoney.from_str("-900.00", EUR),
                delta=SignedMoney.from_str("0.00", EUR),
                percent=Decimal("100.00"),
            ),
        ]

        s = budget_synthesis(comparisons, currency=EUR)
        assert s.total_income_planned.amount == Decimal("3000.00")
        assert s.total_income_actual.amount == Decimal("2800.00")
        assert s.total_expense_planned.amount == Decimal("900.00")
        assert s.total_expense_actual.amount == Decimal("-900.00")
        assert s.net_planned.amount == Decimal("2100.00")
        assert s.net_actual.amount == Decimal("1900.00")


# ---------------------------------------------------------------------------
# Tests API — intégration
# ---------------------------------------------------------------------------

class TestBudgetEnvelopesAPI:

    def test_put_creates_envelope(self, client):
        resp = client.put("/budget/envelopes", json={
            "category": "Revenus",
            "kind": "INCOME",
            "amount": "3000.00",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "Revenus"
        assert data["kind"] == "INCOME"
        assert data["amount"] == "3000.00"
        assert data["currency"] == "EUR"
        assert data["profile_id"] == DEFAULT_PROFILE_ID

    def test_put_upserts_existing(self, client):
        client.put("/budget/envelopes", json={
            "category": "Revenus", "kind": "INCOME", "amount": "3000.00"
        })
        resp = client.put("/budget/envelopes", json={
            "category": "Revenus", "kind": "INCOME", "amount": "3500.00"
        })
        assert resp.status_code == 200
        assert resp.json()["amount"] == "3500.00"

        # Vérifier qu'il n'y a qu'une seule enveloppe
        list_resp = client.get("/budget/envelopes")
        assert len(list_resp.json()) == 1

    def test_list_envelopes(self, client):
        client.put("/budget/envelopes", json={"category": "Revenus", "kind": "INCOME", "amount": "3000.00"})
        client.put("/budget/envelopes", json={"category": "Logement", "kind": "EXPENSE", "amount": "900.00"})

        resp = client.get("/budget/envelopes")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_delete_envelope(self, client):
        put_resp = client.put("/budget/envelopes", json={
            "category": "Revenus", "kind": "INCOME", "amount": "3000.00"
        })
        env_id = put_resp.json()["id"]

        del_resp = client.delete(f"/budget/envelopes/{env_id}")
        assert del_resp.status_code == 204

        list_resp = client.get("/budget/envelopes")
        assert list_resp.json() == []

    def test_delete_not_found(self, client):
        resp = client.delete(f"/budget/envelopes/{uuid4()}")
        assert resp.status_code == 404

    def test_comparison_with_transactions(self, client):
        import uuid as _uuid
        # Créer un compte
        acc_id = str(_uuid.uuid4())
        acc_resp = client.post("/accounts", json={
            "id": acc_id,
            "name": "Compte test",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        assert acc_resp.status_code == 201, acc_resp.text
        acc_id = acc_resp.json()["id"]

        # Ajouter une transaction en mars 2026
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-15",
            "amount": "-500.00",
            "kind": "EXPENSE",
            "category": "Vie quotidienne",
            "label": "Courses",
        })

        # Ajouter une enveloppe
        client.put("/budget/envelopes", json={
            "category": "Vie quotidienne", "kind": "EXPENSE", "amount": "600.00"
        })

        resp = client.get("/budget/comparison", params={"month": "2026-03"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == "2026-03"
        assert data["currency"] == "EUR"
        assert "synthesis" in data
        assert "comparisons" in data

        comp = next(c for c in data["comparisons"] if c["category"] == "Vie quotidienne")
        assert comp["planned"] == "600.00"
        assert comp["actual"] == "-500.00"

    def test_comparison_invalid_month(self, client):
        resp = client.get("/budget/comparison", params={"month": "not-a-month"})
        assert resp.status_code == 422

    def test_history_nominal(self, client):
        """GET /budget/history retourne N mois avec synthèse."""
        import uuid as _uuid

        # Compte + transactions sur 3 mois distincts
        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte hist",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2025-10-01",
        })
        acc_id = acc_resp.json()["id"]

        for date_str, amount, kind in [
            ("2025-10-15", "2800.00", "INCOME"),
            ("2025-11-15", "2900.00", "INCOME"),
            ("2025-12-15", "-500.00", "EXPENSE"),
        ]:
            client.post(f"/accounts/{acc_id}/transactions", json={
                "date": date_str,
                "amount": amount,
                "kind": kind,
                "category": "Test",
                "label": "tx",
            })

        resp = client.get("/budget/history", params={"months": 6})
        assert resp.status_code == 200
        data = resp.json()
        assert "months" in data
        assert len(data["months"]) == 6
        assert data["currency"] == "EUR"
        assert "profile_id" in data

        # Vérifier qu'au moins un mois a des données
        months_with_data = [m for m in data["months"] if m["income_actual"] != "0.00" or m["expense_actual"] != "0.00"]
        assert len(months_with_data) > 0

    def test_history_empty_months(self, client):
        """GET /budget/history sur un profil sans transactions retourne des zéros."""
        resp = client.get("/budget/history", params={"months": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["months"]) == 3
        for m in data["months"]:
            assert m["income_actual"] == "0.00"
            assert m["expense_actual"] == "0.00"
            assert m["net_actual"] == "0.00"

    def test_categories_nominal(self, client):
        """GET /budget/categories retourne les catégories utilisées dans les transactions."""
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte cat",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]

        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-01", "amount": "3000.00", "kind": "INCOME",
            "category": "Revenus", "subcategory": "Salaire", "label": "s"
        })
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-05", "amount": "-200.00", "kind": "EXPENSE",
            "category": "Vie quotidienne", "subcategory": "Courses", "label": "c"
        })
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-10", "amount": "-800.00", "kind": "EXPENSE",
            "category": "Logement", "label": "loyer"
        })

        resp = client.get("/budget/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "income" in data
        assert "expense" in data

        income_cats = {item["category"] for item in data["income"]}
        assert "Revenus" in income_cats

        expense_cats = {item["category"] for item in data["expense"]}
        assert "Vie quotidienne" in expense_cats
        assert "Logement" in expense_cats

        # Sous-catégories
        vie_q = next(i for i in data["expense"] if i["category"] == "Vie quotidienne")
        assert "Courses" in vie_q["subcategories"]

    def test_categories_empty_profile(self, client):
        """GET /budget/categories sur profil sans transactions retourne des listes vides."""
        resp = client.get("/budget/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["income"] == []
        assert data["expense"] == []

    def test_multitenant_isolation(self, client, db_engine, db_url):
        from fastapi.testclient import TestClient
        from app.api.main import app
        from app.identity.defaults import DEFAULT_USER2_EMAIL, DEFAULT_TEST_PASSWORD

        # user1 crée une enveloppe
        client.put("/budget/envelopes", json={
            "category": "Revenus", "kind": "INCOME", "amount": "3000.00"
        })

        # user2 ne doit pas voir l'enveloppe de user1
        with TestClient(app) as c2:
            login = c2.post("/auth/login", json={
                "email": DEFAULT_USER2_EMAIL, "password": DEFAULT_TEST_PASSWORD
            })
            token2 = login.json()["access_token"]
            c2.headers.update({"Authorization": f"Bearer {token2}"})
            resp2 = c2.get("/budget/envelopes")
            assert resp2.status_code == 200
            assert resp2.json() == []
