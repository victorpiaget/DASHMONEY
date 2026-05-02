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
from app.engine.budget import (
    BudgetComparison,
    budget_synthesis,
    budget_vs_actual,
    compute_savings,
    expense_buckets_by_nature,
    expense_total_excluding_savings,
    expense_totals_by_category,
    income_totals_by_category,
    median_monthly_totals_by_category,
    BucketTotals,
)
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

    def test_transfer_excluded_from_expense_totals(self):
        """Un Transfer ne doit pas apparaître dans expense_totals_by_category()."""
        expense = _make_tx(
            category="Vie quotidienne",
            kind=TransactionKind.EXPENSE,
            amount_str="-150.00",
        )
        transfer_neg = Transaction.create(
            account_id="acc-1",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("-500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert interne",
        )
        transfer_pos = Transaction.create(
            account_id="acc-2",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert interne",
        )

        totals = expense_totals_by_category(
            [expense, transfer_neg, transfer_pos], currency=EUR,
        )
        cats = {t.category for t in totals}
        assert "Transfert interne" not in cats
        assert "Vie quotidienne" in cats

    def test_transfer_excluded_from_synthesis(self):
        """Un Transfer ne doit ni gonfler income ni gonfler expense dans le total."""
        income = _make_tx(category="Revenus", kind=TransactionKind.INCOME, amount_str="2800.00")
        transfer_neg = Transaction.create(
            account_id="acc-1",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("-500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert interne",
        )
        transfer_pos = Transaction.create(
            account_id="acc-2",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert interne",
        )

        comparisons = budget_vs_actual([], [income, transfer_neg, transfer_pos], currency=EUR)
        s = budget_synthesis(comparisons, currency=EUR)
        assert s.total_income_actual.amount == Decimal("2800.00")
        assert s.total_expense_actual.amount == Decimal("0.00")

    def test_expense_overspent(self):
        env = _make_env(category="Vie quotidienne", kind=TransactionKind.EXPENSE, amount_str="500.00")
        tx = _make_tx(category="Vie quotidienne", kind=TransactionKind.EXPENSE, amount_str="-650.00")

        result = budget_vs_actual([env], [tx], currency=EUR)
        assert len(result) == 1
        c = result[0]
        # delta positif = dépassement pour les dépenses
        assert c.delta.amount == Decimal("150.00")
        assert c.percent == Decimal("130.00")


class TestExpenseBucketsByNature:

    def test_groups_by_nature(self):
        nature_map = {
            "Loyer": "NEED",
            "Restaurants": "WANT",
            "PEA": "SAVING",
        }
        txs = [
            _make_tx(category="Loyer", kind=TransactionKind.EXPENSE, amount_str="-900.00"),
            _make_tx(category="Restaurants", kind=TransactionKind.EXPENSE, amount_str="-150.00"),
            _make_tx(category="PEA", kind=TransactionKind.EXPENSE, amount_str="-500.00"),
        ]
        result = expense_buckets_by_nature(txs, nature_map, currency=EUR)
        assert result.needs.amount == Decimal("-900.00")
        assert result.wants.amount == Decimal("-150.00")
        assert result.savings.amount == Decimal("-500.00")
        assert result.uncategorized.amount == Decimal("0.00")

    def test_unknown_category_falls_into_uncategorized(self):
        nature_map = {"Loyer": "NEED"}
        txs = [
            _make_tx(category="Loyer", kind=TransactionKind.EXPENSE, amount_str="-900.00"),
            _make_tx(category="MysteryCat", kind=TransactionKind.EXPENSE, amount_str="-50.00"),
        ]
        result = expense_buckets_by_nature(txs, nature_map, currency=EUR)
        assert result.needs.amount == Decimal("-900.00")
        assert result.uncategorized.amount == Decimal("-50.00")

    def test_null_nature_falls_into_uncategorized(self):
        nature_map = {"Catégorie": None}
        txs = [
            _make_tx(category="Catégorie", kind=TransactionKind.EXPENSE, amount_str="-30.00"),
        ]
        result = expense_buckets_by_nature(txs, nature_map, currency=EUR)
        assert result.uncategorized.amount == Decimal("-30.00")
        assert result.needs.amount == Decimal("0.00")

    def test_income_and_transfer_excluded(self):
        nature_map = {"Salaire": "NEED", "Transfert": "NEED"}
        income = _make_tx(category="Salaire", kind=TransactionKind.INCOME, amount_str="2500.00")
        transfer = Transaction.create(
            account_id="acc-1",
            date=dt.date(2026, 3, 15),
            sequence=1,
            amount=SignedMoney.from_str("-500.00", EUR),
            kind=TransactionKind.TRANSFER,
            category="Transfert",
        )
        result = expense_buckets_by_nature([income, transfer], nature_map, currency=EUR)
        assert result.needs.amount == Decimal("0.00")
        assert result.uncategorized.amount == Decimal("0.00")

    def test_total_expenses_excludes_savings(self):
        nature_map = {
            "Loyer": "NEED",
            "Restaurants": "WANT",
            "PEA": "SAVING",
            "Inconnue": None,
        }
        txs = [
            _make_tx(category="Loyer", kind=TransactionKind.EXPENSE, amount_str="-900.00"),
            _make_tx(category="Restaurants", kind=TransactionKind.EXPENSE, amount_str="-150.00"),
            _make_tx(category="PEA", kind=TransactionKind.EXPENSE, amount_str="-500.00"),
            _make_tx(category="Inconnue", kind=TransactionKind.EXPENSE, amount_str="-30.00"),
        ]
        buckets = expense_buckets_by_nature(txs, nature_map, currency=EUR)
        total = expense_total_excluding_savings(buckets, currency=EUR)
        # NEED + WANT + UNCAT, sans SAVING
        assert total.amount == Decimal("-1080.00")


class TestComputeSavings:

    def _make_buckets(self, savings_amount: str) -> BucketTotals:
        z = SignedMoney.from_str("0.00", EUR)
        return BucketTotals(
            needs=z, wants=z, savings=SignedMoney.from_str(savings_amount, EUR), uncategorized=z,
        )

    def test_nominal(self):
        buckets = self._make_buckets("-500.00")
        income = SignedMoney.from_str("2500.00", EUR)
        savings, rate = compute_savings(buckets, income, currency=EUR)
        assert savings.amount == Decimal("500.00")
        assert rate == Decimal("0.2000")

    def test_zero_income_returns_zero_rate(self):
        buckets = self._make_buckets("-500.00")
        income = SignedMoney.from_str("0.00", EUR)
        savings, rate = compute_savings(buckets, income, currency=EUR)
        assert savings.amount == Decimal("500.00")
        assert rate == Decimal("0.0000")

    def test_negative_income_returns_zero_rate(self):
        buckets = self._make_buckets("-100.00")
        income = SignedMoney.from_str("-50.00", EUR)
        _, rate = compute_savings(buckets, income, currency=EUR)
        assert rate == Decimal("0.0000")

    def test_no_savings(self):
        buckets = self._make_buckets("0.00")
        income = SignedMoney.from_str("2500.00", EUR)
        savings, rate = compute_savings(buckets, income, currency=EUR)
        assert savings.amount == Decimal("0.00")
        assert rate == Decimal("0.0000")


class TestMedianMonthlyTotalsByCategory:

    def _tx(self, *, category, amount, year, month, day=15, kind=TransactionKind.EXPENSE):
        return Transaction.create(
            account_id="acc",
            date=dt.date(year, month, day),
            sequence=1,
            amount=SignedMoney.from_str(amount, EUR),
            kind=kind,
            category=category,
        )

    def test_excludes_categories_with_single_occurrence(self):
        txs = [
            self._tx(category="Loyer", amount="-900.00", year=2026, month=1),
            self._tx(category="Loyer", amount="-900.00", year=2026, month=2),
            self._tx(category="Loyer", amount="-900.00", year=2026, month=3),
            self._tx(category="OneShot", amount="-50.00", year=2026, month=2),
        ]
        result = median_monthly_totals_by_category(
            txs, months=[(2026, 1), (2026, 2), (2026, 3)], currency=EUR,
        )
        cats = [c.category for c in result]
        assert "Loyer" in cats
        assert "OneShot" not in cats

    def test_median_odd_count(self):
        txs = [
            self._tx(category="Resto", amount="-100.00", year=2026, month=1),
            self._tx(category="Resto", amount="-200.00", year=2026, month=2),
            self._tx(category="Resto", amount="-300.00", year=2026, month=3),
        ]
        result = median_monthly_totals_by_category(
            txs, months=[(2026, 1), (2026, 2), (2026, 3)], currency=EUR,
        )
        assert len(result) == 1
        assert result[0].median_amount.amount == Decimal("200.00")
        assert result[0].occurrences == 3

    def test_median_even_count(self):
        txs = [
            self._tx(category="Courses", amount="-100.00", year=2026, month=1),
            self._tx(category="Courses", amount="-300.00", year=2026, month=2),
        ]
        result = median_monthly_totals_by_category(
            txs, months=[(2026, 1), (2026, 2)], currency=EUR,
        )
        assert result[0].median_amount.amount == Decimal("200.00")

    def test_excludes_transfers(self):
        txs = [
            Transaction.create(
                account_id="acc",
                date=dt.date(2026, 1, 15),
                sequence=1,
                amount=SignedMoney.from_str("-500.00", EUR),
                kind=TransactionKind.TRANSFER,
                category="Transfert",
            ),
            Transaction.create(
                account_id="acc",
                date=dt.date(2026, 2, 15),
                sequence=1,
                amount=SignedMoney.from_str("-500.00", EUR),
                kind=TransactionKind.TRANSFER,
                category="Transfert",
            ),
        ]
        result = median_monthly_totals_by_category(
            txs, months=[(2026, 1), (2026, 2)], currency=EUR,
        )
        assert result == []

    def test_aggregates_multiple_txs_in_same_month(self):
        txs = [
            self._tx(category="Resto", amount="-50.00", year=2026, month=1),
            self._tx(category="Resto", amount="-50.00", year=2026, month=1, day=20),
            self._tx(category="Resto", amount="-300.00", year=2026, month=2),
        ]
        result = median_monthly_totals_by_category(
            txs, months=[(2026, 1), (2026, 2)], currency=EUR,
        )
        assert result[0].median_amount.amount == Decimal("200.00")  # médiane(100, 300) = 200


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

    def test_comparison_income_consistent_when_only_subcategories(self, client):
        """Synthesis.total_income_actual == somme des comparisons INCOME, même
        quand les revenus n'ont qu'une sous-catégorie (jamais de ligne au niveau
        catégorie root). Garde-fou pour le bug "Section Revenus vide"."""
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte revenus",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]

        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-05", "amount": "1500.00", "kind": "INCOME",
            "category": "Revenus", "subcategory": "Salaire", "label": "salaire",
        })
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-20", "amount": "575.65", "kind": "INCOME",
            "category": "Revenus", "subcategory": "Bourses", "label": "bourse",
        })

        resp = client.get("/budget/comparison", params={"month": "2026-03"})
        assert resp.status_code == 200
        data = resp.json()

        income_rows = [c for c in data["comparisons"] if c["kind"] == "INCOME"]
        # Toutes les transactions ayant une subcategory, on n'attend que des
        # lignes de niveau sous-catégorie
        assert all(c["subcategory"] is not None for c in income_rows)
        sum_income = sum(Decimal(c["actual"]) for c in income_rows)
        assert sum_income == Decimal("2075.65")
        assert data["synthesis"]["total_income_actual"] == "2075.65"

    def test_comparison_savings_rate_in_synthesis(self, client):
        """synthesis.savings_actual et savings_rate sont calculés depuis le bucket SAVING."""
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte savings",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]

        client.post("/categories", json={"name": "PEA", "nature": "SAVING"})
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-05", "amount": "2500.00", "kind": "INCOME",
            "category": "Revenus", "subcategory": "Salaire", "label": "s",
        })
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-12", "amount": "-500.00", "kind": "EXPENSE",
            "category": "PEA", "label": "alim",
        })

        resp = client.get("/budget/comparison", params={"month": "2026-03"})
        assert resp.status_code == 200, resp.text
        s = resp.json()["synthesis"]
        assert s["savings_actual"] == "500.00"
        assert s["savings_rate"] == "0.2000"

    def test_comparison_savings_rate_zero_when_no_income(self, client):
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte sans revenus",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]
        client.post("/categories", json={"name": "PEA", "nature": "SAVING"})
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-12", "amount": "-200.00", "kind": "EXPENSE",
            "category": "PEA", "label": "alim",
        })

        resp = client.get("/budget/comparison", params={"month": "2026-03"})
        s = resp.json()["synthesis"]
        assert s["savings_actual"] == "200.00"
        assert s["savings_rate"] == "0.0000"

    def test_history_includes_savings(self, client):
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte hist savings",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2025-01-01",
        })
        acc_id = acc_resp.json()["id"]
        client.post("/categories", json={"name": "PEA", "nature": "SAVING"})

        # 2 mois différents — vérifions juste la présence des champs
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2025-12-05", "amount": "2000.00", "kind": "INCOME",
            "category": "Revenus", "label": "s",
        })
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2025-12-15", "amount": "-400.00", "kind": "EXPENSE",
            "category": "PEA", "label": "pea",
        })

        resp = client.get("/budget/history", params={"months": 6})
        assert resp.status_code == 200
        for m in resp.json()["months"]:
            assert "savings_actual" in m
            assert "savings_rate" in m

    def test_categories_includes_nature(self, client):
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte cat-nature",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]
        client.post("/categories", json={"name": "Logement", "nature": "NEED"})
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": "2026-03-01", "amount": "-900.00", "kind": "EXPENSE",
            "category": "Logement", "subcategory": "Loyer", "label": "loyer",
        })

        resp = client.get("/budget/categories")
        data = resp.json()
        logement = next(c for c in data["expense"] if c["category"] == "Logement")
        assert logement["nature"] == "NEED"

    def test_auto_budget_nominal(self, client):
        """GET /budget/auto-budget retourne la médiane des N derniers mois pleins."""
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte auto-budget",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2025-01-01",
        })
        acc_id = acc_resp.json()["id"]
        client.post("/categories", json={"name": "Loyer", "nature": "NEED"})

        # Mois -3, -2, -1 par rapport à aujourd'hui
        today = dt.date.today()
        recent_months: list[tuple[int, int]] = []
        for i in range(1, 4):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1
            recent_months.append((y, m))

        for (y, m), amount in zip(recent_months, ["-900.00", "-900.00", "-900.00"]):
            client.post(f"/accounts/{acc_id}/transactions", json={
                "date": f"{y}-{m:02d}-15",
                "amount": amount,
                "kind": "EXPENSE",
                "category": "Loyer",
                "label": "loyer",
            })

        resp = client.get("/budget/auto-budget", params={"months": 3})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["based_on_months"] == 3
        loyer = next(s for s in data["suggestions"] if s["category"] == "Loyer")
        assert loyer["median_amount"] == "900.00"
        assert loyer["nature"] == "NEED"
        assert loyer["occurrences"] == 3

    def test_auto_budget_excludes_single_occurrence(self, client):
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte single",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2025-01-01",
        })
        acc_id = acc_resp.json()["id"]

        # Un seul mois passé
        today = dt.date.today()
        y = today.year
        m = today.month - 1
        while m <= 0:
            m += 12
            y -= 1
        client.post(f"/accounts/{acc_id}/transactions", json={
            "date": f"{y}-{m:02d}-15",
            "amount": "-50.00",
            "kind": "EXPENSE",
            "category": "OneShot",
            "label": "x",
        })

        resp = client.get("/budget/auto-budget", params={"months": 3})
        assert resp.status_code == 200
        cats = [s["category"] for s in resp.json()["suggestions"]]
        assert "OneShot" not in cats

    def test_comparison_buckets_by_nature(self, client):
        """GET /budget/comparison expose les buckets needs/wants/savings/uncategorized
        selon la nature des catégories. Le total dépenses exclut SAVING."""
        import uuid as _uuid

        acc_resp = client.post("/accounts", json={
            "id": str(_uuid.uuid4()),
            "name": "Compte buckets",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "EUR",
            "opened_on": "2026-01-01",
        })
        acc_id = acc_resp.json()["id"]

        # Créer 3 catégories typées + 1 sans nature
        cats = {}
        for name, nature in [
            ("Loyer", "NEED"),
            ("Resto", "WANT"),
            ("PEA", "SAVING"),
            ("Mystère", None),
        ]:
            r = client.post("/categories", json={"name": name, "nature": nature})
            cats[name] = r.json()

        # Transactions associées (les catégories des transactions sont des strings,
        # le matching se fait sur le NOM de la catégorie)
        for cat_name, amount in [
            ("Loyer", "-900.00"),
            ("Resto", "-120.00"),
            ("PEA", "-500.00"),
            ("Mystère", "-40.00"),
        ]:
            client.post(f"/accounts/{acc_id}/transactions", json={
                "date": "2026-03-15",
                "amount": amount,
                "kind": "EXPENSE",
                "category": cat_name,
                "label": "tx",
            })

        resp = client.get("/budget/comparison", params={"month": "2026-03"})
        assert resp.status_code == 200, resp.text
        buckets = resp.json()["buckets"]
        assert buckets["needs"] == "-900.00"
        assert buckets["wants"] == "-120.00"
        assert buckets["savings"] == "-500.00"
        assert buckets["uncategorized"] == "-40.00"
        # Total exclut savings : -900 + -120 + -40 = -1060
        assert buckets["total_expenses"] == "-1060.00"

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
