#!/usr/bin/env python3
"""
seed_demo.py — Crée les utilisateurs de démonstration dans dashmoney_demo.

Scénario :
  - Lea Dupont (lea@dashmoney.app)  — PM 35 ans, 4 ans d'historique complet
  - Thomas Bernard (thomas@dashmoney.app) — Dev freelance 33 ans, depuis 2025

Relations workspace :
  - Lea est OWNER de son workspace "Lea Dupont"
  - Thomas est OWNER de son workspace "Thomas Bernard"
  - Thomas est invité dans le workspace de Lea en MEMBER avec accès READ
    → Thomas voit le patrimoine de Lea mais ne peut pas le modifier

Usage (depuis backend/) :
    DASHMONEY_SECRET_KEY=demo-key python scripts/seed_demo.py

DB cible : postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_demo
"""
from __future__ import annotations

import os
import sys
import subprocess
import datetime as dt
from decimal import Decimal
from uuid import UUID
import random

random.seed(42)

DEMO_DB_URL = os.environ.get(
    "DASHMONEY_DEMO_DATABASE_URL",
    "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_demo",
)
DEMO_DB_NAME = DEMO_DB_URL.rsplit("/", 1)[1]

os.environ["DASHMONEY_DATABASE_URL"] = DEMO_DB_URL
os.environ.setdefault("DASHMONEY_SECRET_KEY", "demo-secret-key-not-for-production-32ch")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────────────────────
# IDs fixes
# ─────────────────────────────────────────────────────────────────────────────

# Lea
LEA_USER_ID      = "d0000000-0000-0000-0000-000000000001"
LEA_WORKSPACE_ID = "d0000000-0000-0000-0000-000000000002"
LEA_PROFILE_ID   = "d0000000-0000-0000-0000-000000000003"
LEA_EMAIL        = "lea@dashmoney.app"

# Thomas
THO_USER_ID      = "d0000000-0000-0000-0000-000000000011"
THO_WORKSPACE_ID = "d0000000-0000-0000-0000-000000000012"
THO_PROFILE_ID   = "d0000000-0000-0000-0000-000000000013"
THO_EMAIL        = "thomas@dashmoney.app"

DEMO_PASSWORD = "Demo1234!"

# Comptes Lea
ACC_CHQ_BNP    = "demo-chq-bnp"
ACC_SAV_LA     = "demo-sav-livreta"
ACC_SAV_LDDS   = "demo-sav-ldds"
ACC_CHQ_JOINT  = "demo-chq-joint"

# Portefeuilles Lea
PF_PEA_UUID    = UUID("aa000001-0000-0000-0000-000000000001")
PF_CTO_UUID    = UUID("bb000002-0000-0000-0000-000000000002")
PF_CRYPTO_UUID = UUID("cc000003-0000-0000-0000-000000000003")
PF_PEA_CASH    = f"pt_{PF_PEA_UUID.hex}_cash"
PF_CTO_CASH    = f"pt_{PF_CTO_UUID.hex}_cash"
PF_CRYPTO_CASH = f"pt_{PF_CRYPTO_UUID.hex}_cash"

# Comptes Thomas
THO_CHQ       = "thomas-chq-bourso"
THO_SAV_LA    = "thomas-sav-livreta"

# Portefeuille Thomas
PF_THO_CTO_UUID = UUID("dd000004-0000-0000-0000-000000000004")
PF_THO_CTO_CASH = f"pt_{PF_THO_CTO_UUID.hex}_cash"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def d(year: int, month: int, day: int = 1) -> dt.date:
    return dt.date(year, month, day)

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def jitter(base: float, pct: float = 0.04) -> Decimal:
    v = base * (1 + random.uniform(-pct, pct))
    return Decimal(f"{v:.2f}")

def months_range(start: dt.date, end: dt.date) -> list[dt.date]:
    out = []
    cur = dt.date(start.year, start.month, 1)
    end = dt.date(end.year, end.month, 1)
    while cur <= end:
        out.append(cur)
        cur = dt.date(cur.year + 1, 1, 1) if cur.month == 12 else dt.date(cur.year, cur.month + 1, 1)
    return out

LEA_MONTHS = months_range(d(2022, 1), d(2026, 3))   # 51 mois
THO_MONTHS = months_range(d(2025, 2), d(2026, 3))   # 14 mois


# ─────────────────────────────────────────────────────────────────────────────
# DB bootstrap
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_db_exists() -> None:
    """Drop + recreate la DB demo pour repartir d'un etat propre."""
    import psycopg
    base_url = DEMO_DB_URL.rsplit("/", 1)[0]
    pg_url = base_url.replace("postgresql+psycopg://", "postgresql://") + "/postgres"
    with psycopg.connect(pg_url, autocommit=True) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DEMO_DB_NAME,)
        ).fetchone()
        if row is not None:
            print(f"[seed_demo] Drop de l'ancienne base '{DEMO_DB_NAME}'...")
            # Ferme les connexions actives avant de dropper
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (DEMO_DB_NAME,)
            )
            conn.execute(f'DROP DATABASE "{DEMO_DB_NAME}"')
        print(f"[seed_demo] Creation de la base '{DEMO_DB_NAME}'...")
        conn.execute(f'CREATE DATABASE "{DEMO_DB_NAME}"')


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    _ensure_db_exists()

    from app.db import get_engine, get_session_factory
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    from app.repositories import sql_account_repository             # noqa
    from app.repositories import sql_transaction_repository         # noqa
    from app.repositories import sql_instrument_repository          # noqa
    from app.repositories import sql_trade_repository               # noqa
    from app.repositories import sql_portfolio_repository           # noqa
    from app.repositories import sql_portfolio_snapshot_repository  # noqa
    from app.repositories import sql_price_repository               # noqa
    from app.repositories import sql_identity_models                # noqa
    from app.repositories import sql_identity_repository            # noqa
    from app.repositories import sql_category_repository            # noqa
    from app.repositories import sql_exchange_rate_repository       # noqa
    from app.repositories import sql_refresh_token_repository       # noqa
    from app.repositories import sql_user_repository                # noqa

    from app.db_base import Base
    engine = get_engine()

    # create_all cree le schema complet depuis les modeles SQLAlchemy courants
    print("[seed_demo] Creation du schema (create_all)...")
    Base.metadata.create_all(bind=engine)

    # Stamp Alembic a head pour qu'il sache que le schema est a jour
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", "head"],
        cwd=backend_dir,
        env=os.environ.copy(),
        check=True,
    )

    SessionLocal = get_session_factory()
    with SessionLocal() as s:
        _seed_identity(s);          s.flush()
        _seed_instruments(s);       s.flush()
        # ── Lea ──
        _seed_lea_accounts(s);      s.flush()
        _seed_lea_transactions(s);  s.flush()
        _seed_lea_portfolios(s);    s.flush()
        _seed_lea_trades(s);        s.flush()
        _seed_lea_snapshots(s);     s.flush()
        # ── Thomas ──
        _seed_thomas_accounts(s);      s.flush()
        _seed_thomas_transactions(s);  s.flush()
        _seed_thomas_portfolio(s);     s.flush()
        _seed_thomas_trades(s);        s.flush()
        _seed_thomas_snapshots(s);     s.flush()
        # ── Prix + taux de change (partagés) ──
        _seed_prices(s);            s.flush()
        _seed_exchange_rates(s);    s.flush()
        s.commit()

    print("\n[seed_demo] Termine !")
    print(f"  Lea     : {LEA_EMAIL}    / {DEMO_PASSWORD}  (OWNER workspace Lea)")
    print(f"  Thomas  : {THO_EMAIL} / {DEMO_PASSWORD}  (OWNER workspace Thomas + MEMBER workspace Lea)")
    print(f"  DB      : {DEMO_DB_NAME}")


# ─────────────────────────────────────────────────────────────────────────────
# Identity — Lea + Thomas + relations workspace
# ─────────────────────────────────────────────────────────────────────────────
def _seed_identity(s) -> None:
    from app.identity.auth import hash_password
    from app.repositories.sql_identity_models import (
        UserRow, WorkspaceRow, ProfileRow,
        WorkspaceMembershipRow, WorkspaceProfileLinkRow, ProfileAccessRow,
    )

    print("[seed_demo] Identite (Lea + Thomas + partage workspace)...")
    pw = hash_password(DEMO_PASSWORD)

    # ── Lea ──────────────────────────────────────────────────────────────────
    s.add(UserRow(id=LEA_USER_ID, email=LEA_EMAIL, password_hash=pw, is_disabled=False))
    s.add(WorkspaceRow(id=LEA_WORKSPACE_ID, name="Lea Dupont"))
    s.flush()
    s.add(ProfileRow(id=LEA_PROFILE_ID, workspace_id=LEA_WORKSPACE_ID, display_name="Patrimoine"))
    s.flush()
    s.add(WorkspaceProfileLinkRow(workspace_id=LEA_WORKSPACE_ID, profile_id=LEA_PROFILE_ID))
    s.add(WorkspaceMembershipRow(workspace_id=LEA_WORKSPACE_ID, user_id=LEA_USER_ID, role="OWNER"))
    s.flush()
    s.add(ProfileAccessRow(profile_id=LEA_PROFILE_ID, user_id=LEA_USER_ID, permission="ADMIN"))

    # ── Thomas ───────────────────────────────────────────────────────────────
    s.add(UserRow(id=THO_USER_ID, email=THO_EMAIL, password_hash=pw, is_disabled=False))
    s.add(WorkspaceRow(id=THO_WORKSPACE_ID, name="Thomas Bernard"))
    s.flush()
    s.add(ProfileRow(id=THO_PROFILE_ID, workspace_id=THO_WORKSPACE_ID, display_name="Perso"))
    s.flush()
    s.add(WorkspaceProfileLinkRow(workspace_id=THO_WORKSPACE_ID, profile_id=THO_PROFILE_ID))
    s.add(WorkspaceMembershipRow(workspace_id=THO_WORKSPACE_ID, user_id=THO_USER_ID, role="OWNER"))
    s.flush()
    s.add(ProfileAccessRow(profile_id=THO_PROFILE_ID, user_id=THO_USER_ID, permission="ADMIN"))

    # ── Thomas invité dans le workspace de Lea ───────────────────────────────
    # Role workspace : MEMBER (peut lister les profils mais pas administrer)
    s.add(WorkspaceMembershipRow(workspace_id=LEA_WORKSPACE_ID, user_id=THO_USER_ID, role="MEMBER"))
    s.flush()
    # Accès profil : READ seulement (consultation sans modification)
    s.add(ProfileAccessRow(profile_id=LEA_PROFILE_ID, user_id=THO_USER_ID, permission="READ"))

    print("[seed_demo]   Thomas peut consulter le patrimoine de Lea (READ) mais pas le modifier.")


# ─────────────────────────────────────────────────────────────────────────────
# Instruments (partagés, pas de profile_id)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_instruments(s) -> None:
    from app.repositories.sql_instrument_repository import InstrumentRow

    print("[seed_demo] Instruments...")
    items = [
        ("MC.PA",    "STOCK", "EUR", "LVMH Moet Hennessy",           "MC.PA"),
        ("TTE.PA",   "STOCK", "EUR", "TotalEnergies",                "TTE.PA"),
        ("AIR.PA",   "STOCK", "EUR", "Airbus Group",                 "AIR.PA"),
        ("BNP.PA",   "STOCK", "EUR", "BNP Paribas",                  "BNP.PA"),
        ("CW8.PA",   "ETF",   "EUR", "Amundi MSCI World UCITS ETF",  "CW8.PA"),
        ("PAEEM.PA", "ETF",   "EUR", "Amundi PEA MSCI Emerging",     "PAEEM.PA"),
        ("AAPL",     "STOCK", "USD", "Apple Inc.",                   "AAPL"),
        ("MSFT",     "STOCK", "USD", "Microsoft Corporation",        "MSFT"),
        ("NVDA",     "STOCK", "USD", "NVIDIA Corporation",           "NVDA"),
        ("BTC-EUR",  "CRYPTO","EUR", "Bitcoin",                      "BTC-EUR"),
        ("ETH-EUR",  "CRYPTO","EUR", "Ethereum",                     "ETH-EUR"),
    ]
    for sym, kind, cur, name, ticker in items:
        s.add(InstrumentRow(symbol=sym, kind=kind, currency=cur, name=name, ticker=ticker))


# ─────────────────────────────────────────────────────────────────────────────
# Lea — Comptes
# ─────────────────────────────────────────────────────────────────────────────
def _seed_lea_accounts(s) -> None:
    from app.repositories.sql_account_repository import AccountRow

    print("[seed_demo] Comptes Lea...")
    for acc_id, name, cur, bal, opened, atype in [
        (ACC_CHQ_BNP,   "BNP Compte Courant",        "EUR", "2000.00", d(2019, 3, 1), "CHECKING"),
        (ACC_SAV_LA,    "Livret A Banque Postale",   "EUR", "0.00",   d(2019, 3, 1), "SAVINGS"),
        (ACC_SAV_LDDS,  "LDDS BNP",                  "EUR", "0.00",   d(2020, 6, 1), "SAVINGS"),
        (ACC_CHQ_JOINT, "Compte Joint CIC",           "EUR", "1000.00",d(2021, 6, 1), "CHECKING"),
        (PF_PEA_CASH,   "PEA Boursorama - Cash",     "EUR", "0.00",   d(2022, 1, 1), "INVESTMENT"),
        (PF_CTO_CASH,   "CTO Degiro - Cash",          "EUR", "0.00",   d(2022, 3, 1), "INVESTMENT"),
        (PF_CRYPTO_CASH,"Binance - Cash EUR",         "EUR", "0.00",   d(2022, 1, 1), "INVESTMENT"),
    ]:
        s.add(AccountRow(
            id=acc_id, name=name, currency=cur,
            opening_balance=Decimal(bal), opened_on=opened,
            account_type=atype, profile_id=LEA_PROFILE_ID,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Lea — Transactions (2022-01 → 2026-03)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_lea_transactions(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_transaction_repository import TransactionRow

    print(f"[seed_demo] Transactions Lea ({len(LEA_MONTHS)} mois)...")
    rows = []
    now = utcnow()

    for mo in LEA_MONTHS:
        yr, mth = mo.year, mo.month
        seq = 1

        def tx(acc, day, amount, kind, cat, subcat=None, label=None, tid=None):
            nonlocal seq
            rows.append(TransactionRow(
                id=str(uuid4()), account_id=acc,
                day=day, sequence=seq, amount=amount, currency="EUR",
                kind=kind, category=cat, subcategory=subcat,
                label=label, created_at=now, transfer_id=tid,
                profile_id=LEA_PROFILE_ID,
            ))
            seq += 1

        # Salaire
        tx(ACC_CHQ_BNP, d(yr, mth, 5), jitter(3800, 0.01),
           "INCOME", "Revenus", "Salaire", "Virement salaire")

        # Prime décembre
        if mth == 12:
            tx(ACC_CHQ_BNP, d(yr, mth, 20), Decimal("2000.00"),
               "INCOME", "Revenus", "Prime", "Prime annuelle")

        # Loyer
        tx(ACC_CHQ_BNP, d(yr, mth, 1), Decimal("-1200.00"),
           "EXPENSE", "Logement", "Loyer", "Loyer mensuel")

        # Courses
        tx(ACC_CHQ_BNP, d(yr, mth, 15), -jitter(250, 0.15),
           "EXPENSE", "Alimentation", "Courses", "Courses semaine")

        # Restaurant
        tx(ACC_CHQ_BNP, d(yr, mth, 20), -jitter(130, 0.25),
           "EXPENSE", "Alimentation", "Restaurant", "Sorties restaurants")

        # Transport
        tx(ACC_CHQ_BNP, d(yr, mth, 5), -jitter(98, 0.10),
           "EXPENSE", "Transport", "Transports en commun", "Navigo mensuel")

        # Abonnements
        tx(ACC_CHQ_BNP, d(yr, mth, 10), Decimal("-55.00"),
           "EXPENSE", "Loisirs", "Abonnements", "Netflix / Spotify / Mobile")

        # Electricite bimestriel
        if mth % 2 == 0:
            tx(ACC_CHQ_BNP, d(yr, mth, 12), -jitter(185, 0.20),
               "EXPENSE", "Logement", "Energie", "EDF bimestriel")

        # Sante + remboursement
        if mth % 3 == 0:
            tx(ACC_CHQ_BNP, d(yr, mth, 18), -jitter(45, 0.40),
               "EXPENSE", "Sante", "Medecin", "Consultation medecin")
            tx(ACC_CHQ_BNP, d(yr, mth, 25), Decimal("22.00"),
               "INCOME", "Sante", "Remboursement secu", "CPAM remboursement")

        # Loisirs
        if mth % 2 == 1:
            tx(ACC_CHQ_BNP, d(yr, mth, 22), -jitter(80, 0.40),
               "EXPENSE", "Loisirs", "Sorties", "Cinema / concerts")

        # Shopping
        if mth in (3, 4, 9, 10):
            tx(ACC_CHQ_BNP, d(yr, mth, 17), -jitter(120, 0.50),
               "EXPENSE", "Shopping", "Vetements", "Achat vetements")

        # Vacances ete
        if mth == 7:
            tx(ACC_CHQ_BNP, d(yr, mth, 5), -jitter(900, 0.20),
               "EXPENSE", "Vacances", "Voyage", "Vacances d'ete")

        # Virements vers epargne (avec transfer_id pour les paires)
        tid_la   = str(uuid4())
        tid_ldds = str(uuid4())

        tx(ACC_CHQ_BNP, d(yr, mth, 28), Decimal("-300.00"),
           "TRANSFER", "Virement", "Epargne", "Virement Livret A", tid_la)
        # Cote livret A — sequence propre
        la_seq = sum(1 for r in rows if r.account_id == ACC_SAV_LA and r.day == d(yr, mth, 28)) + 1
        rows.append(TransactionRow(
            id=str(uuid4()), account_id=ACC_SAV_LA,
            day=d(yr, mth, 28), sequence=la_seq, amount=Decimal("300.00"), currency="EUR",
            kind="TRANSFER", category="Virement", subcategory="Epargne",
            label="Virement depuis BNP", created_at=now,
            transfer_id=tid_la, profile_id=LEA_PROFILE_ID,
        ))

        tx(ACC_CHQ_BNP, d(yr, mth, 28), Decimal("-100.00"),
           "TRANSFER", "Virement", "Epargne", "Virement LDDS", tid_ldds)
        ldds_seq = sum(1 for r in rows if r.account_id == ACC_SAV_LDDS and r.day == d(yr, mth, 28)) + 1
        rows.append(TransactionRow(
            id=str(uuid4()), account_id=ACC_SAV_LDDS,
            day=d(yr, mth, 28), sequence=ldds_seq, amount=Decimal("100.00"), currency="EUR",
            kind="TRANSFER", category="Virement", subcategory="Epargne",
            label="Virement depuis BNP", created_at=now,
            transfer_id=tid_ldds, profile_id=LEA_PROFILE_ID,
        ))

        # Interets Livret A en janvier
        if mth == 1 and yr > 2022:
            la_int_seq = sum(1 for r in rows if r.account_id == ACC_SAV_LA and r.day == d(yr, mth, 2)) + 1
            rows.append(TransactionRow(
                id=str(uuid4()), account_id=ACC_SAV_LA,
                day=d(yr, mth, 2), sequence=la_int_seq,
                amount=jitter(108, 0.02), currency="EUR",
                kind="INCOME", category="Revenus", subcategory="Interets",
                label="Interets Livret A", created_at=now, profile_id=LEA_PROFILE_ID,
            ))

        seq = 1  # reset pour mois suivant sur CHQ_BNP — chaque mois repart à 1

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} transactions Lea inserees.")


# ─────────────────────────────────────────────────────────────────────────────
# Lea — Portefeuilles
# ─────────────────────────────────────────────────────────────────────────────
def _seed_lea_portfolios(s) -> None:
    from app.repositories.sql_portfolio_repository import PortfolioRow

    print("[seed_demo] Portefeuilles Lea...")
    for pf_id, name, cur, ptype, opened, cash_id in [
        (str(PF_PEA_UUID),    "PEA Boursorama",  "EUR", "PEA",             d(2022, 1, 10), PF_PEA_CASH),
        (str(PF_CTO_UUID),    "CTO Degiro",       "EUR", "CTO",             d(2022, 3, 1),  PF_CTO_CASH),
        (str(PF_CRYPTO_UUID), "Binance Crypto",   "EUR", "CRYPTO_EXCHANGE", d(2022, 1, 10), PF_CRYPTO_CASH),
    ]:
        s.add(PortfolioRow(
            id=pf_id, name=name, currency=cur, portfolio_type=ptype,
            opened_on=opened, cash_account_id=cash_id, profile_id=LEA_PROFILE_ID,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Lea — Trades
# ─────────────────────────────────────────────────────────────────────────────
def _seed_lea_trades(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_trade_repository import TradeRow

    print("[seed_demo] Trades Lea...")
    rows = []

    def t(pf: UUID, date, side, sym, qty, price, fees, cur, label=None):
        rows.append(TradeRow(
            id=str(uuid4()), portfolio_id=str(pf), day=date, side=side,
            instrument_symbol=sym, quantity=Decimal(qty), price=Decimal(price),
            fees=Decimal(fees), currency=cur, label=label,
            trade_type="TRADE", linked_cash_tx_id=None, profile_id=LEA_PROFILE_ID,
        ))

    # PEA
    t(PF_PEA_UUID, d(2022, 2, 15), "BUY",  "MC.PA",    "3",  "648.00", "1.99", "EUR", "Achat LVMH x3")
    t(PF_PEA_UUID, d(2022, 6, 10), "BUY",  "CW8.PA",   "10", "382.00", "1.99", "EUR", "Achat CW8 x10")
    t(PF_PEA_UUID, d(2022, 9, 15), "BUY",  "TTE.PA",   "5",  "51.80",  "1.99", "EUR", "Achat TotalEnergies x5")
    t(PF_PEA_UUID, d(2023, 1, 20), "BUY",  "CW8.PA",   "5",  "356.00", "1.99", "EUR", "Renforcement CW8 x5")
    t(PF_PEA_UUID, d(2023, 4, 12), "BUY",  "BNP.PA",   "10", "57.20",  "1.99", "EUR", "Achat BNP x10")
    t(PF_PEA_UUID, d(2023, 6, 15), "BUY",  "AIR.PA",   "2",  "121.00", "1.99", "EUR", "Achat Airbus x2")
    t(PF_PEA_UUID, d(2024, 1, 15), "BUY",  "CW8.PA",   "10", "418.00", "1.99", "EUR", "Renforcement CW8 x10")
    t(PF_PEA_UUID, d(2024, 3, 10), "BUY",  "PAEEM.PA", "20", "44.50",  "1.99", "EUR", "Achat Emerging x20")
    t(PF_PEA_UUID, d(2024, 6, 10), "SELL", "MC.PA",    "1",  "732.00", "1.99", "EUR", "Vente partielle LVMH")
    t(PF_PEA_UUID, d(2025, 1, 20), "BUY",  "CW8.PA",   "5",  "442.00", "1.99", "EUR", "Renforcement CW8 x5")
    t(PF_PEA_UUID, d(2025, 3, 5),  "BUY",  "AIR.PA",   "3",  "158.00", "1.99", "EUR", "Renforcement Airbus x3")
    t(PF_PEA_UUID, d(2025, 6, 15), "BUY",  "TTE.PA",   "5",  "62.50",  "1.99", "EUR", "Renforcement TotalEnergies x5")
    t(PF_PEA_UUID, d(2025, 9, 10), "BUY",  "PAEEM.PA", "10", "48.20",  "1.99", "EUR", "Renforcement Emerging x10")

    # CTO Degiro (EUR — Degiro France gere la conversion USD/EUR en interne)
    t(PF_CTO_UUID, d(2022, 3, 10), "BUY",  "AAPL",  "5",  "150.00", "1.00", "EUR", "Achat Apple x5")
    t(PF_CTO_UUID, d(2022, 9, 20), "BUY",  "MSFT",  "3",  "229.00", "1.00", "EUR", "Achat Microsoft x3")
    t(PF_CTO_UUID, d(2023, 1, 10), "BUY",  "AAPL",  "5",  "116.00", "1.00", "EUR", "Renforcement Apple x5")
    t(PF_CTO_UUID, d(2023, 7, 12), "BUY",  "MSFT",  "2",  "305.00", "1.00", "EUR", "Renforcement Microsoft x2")
    t(PF_CTO_UUID, d(2023,10, 10), "SELL", "AAPL",  "3",  "164.00", "1.00", "EUR", "Vente partielle Apple")
    t(PF_CTO_UUID, d(2024, 2, 5),  "BUY",  "AAPL",  "3",  "171.00", "1.00", "EUR", "Rachat Apple x3")
    t(PF_CTO_UUID, d(2024, 6, 10), "BUY",  "AAPL",  "2",  "180.00", "1.00", "EUR", "Renforcement Apple x2")
    t(PF_CTO_UUID, d(2025, 1, 20), "BUY",  "MSFT",  "2",  "390.00", "1.00", "EUR", "Renforcement Microsoft x2")
    t(PF_CTO_UUID, d(2025, 6, 15), "BUY",  "AAPL",  "2",  "194.00", "1.00", "EUR", "Renforcement Apple x2")

    # Crypto (EUR)
    t(PF_CRYPTO_UUID, d(2022, 1, 10), "BUY",  "BTC-EUR", "0.10", "41000.00", "20.00", "EUR", "Achat BTC 0.1")
    t(PF_CRYPTO_UUID, d(2022, 4, 5),  "BUY",  "ETH-EUR", "1.00", "3200.00",  "5.00",  "EUR", "Achat ETH 1")
    t(PF_CRYPTO_UUID, d(2022, 9, 20), "BUY",  "BTC-EUR", "0.05", "19000.00", "10.00", "EUR", "Renforcement BTC DCA")
    t(PF_CRYPTO_UUID, d(2023, 1, 15), "BUY",  "ETH-EUR", "1.00", "1500.00",  "5.00",  "EUR", "Renforcement ETH DCA")
    t(PF_CRYPTO_UUID, d(2023, 6, 20), "BUY",  "BTC-EUR", "0.05", "26000.00", "12.00", "EUR", "Renforcement BTC DCA")
    t(PF_CRYPTO_UUID, d(2024, 1, 15), "SELL", "BTC-EUR", "0.05", "43000.00", "15.00", "EUR", "Vente partielle BTC")
    t(PF_CRYPTO_UUID, d(2024, 3, 15), "BUY",  "ETH-EUR", "0.50", "3600.00",  "5.00",  "EUR", "Achat ETH 0.5")
    t(PF_CRYPTO_UUID, d(2024,10, 20), "BUY",  "BTC-EUR", "0.02", "67000.00", "10.00", "EUR", "Renforcement BTC")
    t(PF_CRYPTO_UUID, d(2025, 1, 20), "SELL", "ETH-EUR", "1.00", "3200.00",  "8.00",  "EUR", "Vente ETH partielle")
    t(PF_CRYPTO_UUID, d(2025, 4, 10), "BUY",  "BTC-EUR", "0.01", "82000.00", "8.00",  "EUR", "Achat BTC mini")

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} trades Lea inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Lea — Snapshots
# ─────────────────────────────────────────────────────────────────────────────
def _seed_lea_snapshots(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_portfolio_snapshot_repository import PortfolioSnapshotRow

    print("[seed_demo] Snapshots Lea...")
    rows = []

    pea_vals = _curve(LEA_MONTHS, 3900, [
        (d(2022,2),1944),(d(2022,6),3820),(d(2022,9),259),
        (d(2023,1),1780),(d(2023,4),572),(d(2023,6),242),
        (d(2024,1),4180),(d(2024,3),890),(d(2024,6),-732),
        (d(2025,1),2210),(d(2025,3),474),(d(2025,6),313),(d(2025,9),482),
    ], 0.008, 0.025)

    cto_vals = _curve(LEA_MONTHS, 810, [
        (d(2022,3),810),(d(2022,9),744),
        (d(2023,1),625),(d(2023,7),660),(d(2023,10),-531),
        (d(2024,2),555),(d(2024,6),390),
        (d(2025,1),844),(d(2025,6),420),
    ], 0.012, 0.030)

    crypto_vals = _curve(LEA_MONTHS, 4100, [
        (d(2022,1),4100),(d(2022,4),3200),(d(2022,9),950),
        (d(2023,1),1500),(d(2023,6),1300),(d(2024,1),-2150),
        (d(2024,3),1800),(d(2024,10),1340),(d(2025,1),-3200),(d(2025,4),820),
    ], 0.015, 0.12, bear=(d(2022,4),d(2022,12)), bear_factor=-0.04)

    for mo, v in zip(LEA_MONTHS, pea_vals):
        rows.append(PortfolioSnapshotRow(id=str(uuid4()), portfolio_id=str(PF_PEA_UUID),
            day=mo, value=Decimal(f"{max(v,0):.2f}"), currency="EUR", profile_id=LEA_PROFILE_ID))
    for mo, v in zip(LEA_MONTHS, cto_vals):
        rows.append(PortfolioSnapshotRow(id=str(uuid4()), portfolio_id=str(PF_CTO_UUID),
            day=mo, value=Decimal(f"{max(v,0):.2f}"), currency="EUR", profile_id=LEA_PROFILE_ID))
    for mo, v in zip(LEA_MONTHS, crypto_vals):
        rows.append(PortfolioSnapshotRow(id=str(uuid4()), portfolio_id=str(PF_CRYPTO_UUID),
            day=mo, value=Decimal(f"{max(v,0):.2f}"), currency="EUR", profile_id=LEA_PROFILE_ID))

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} snapshots Lea inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Thomas — Comptes
# ─────────────────────────────────────────────────────────────────────────────
def _seed_thomas_accounts(s) -> None:
    from app.repositories.sql_account_repository import AccountRow

    print("[seed_demo] Comptes Thomas...")
    for acc_id, name, cur, bal, opened, atype in [
        (THO_CHQ,        "Boursorama Compte Courant", "EUR", "1500.00", d(2020, 9, 1), "CHECKING"),
        (THO_SAV_LA,     "Livret A Societe Generale", "EUR", "0.00",   d(2020, 9, 1), "SAVINGS"),
        (PF_THO_CTO_CASH,"CTO Trade Republic - Cash", "EUR", "0.00",   d(2025, 2, 1), "INVESTMENT"),
    ]:
        s.add(AccountRow(
            id=acc_id, name=name, currency=cur,
            opening_balance=Decimal(bal), opened_on=opened,
            account_type=atype, profile_id=THO_PROFILE_ID,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Thomas — Transactions (2025-02 → 2026-03, freelance)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_thomas_transactions(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_transaction_repository import TransactionRow

    print(f"[seed_demo] Transactions Thomas ({len(THO_MONTHS)} mois)...")
    rows = []
    now = utcnow()

    # Revenus freelance irréguliers (certains mois ont 2 clients)
    revenus_freelance = {
        d(2025, 2): [("4200.00", "Mission Startup A — Fevrier")],
        d(2025, 3): [("3800.00", "Mission Startup A — Mars"), ("1200.00", "Prestation ponctuelle BankCorp")],
        d(2025, 4): [("4500.00", "Mission Startup A — Avril")],
        d(2025, 5): [("4500.00", "Mission Startup A — Mai"), ("800.00",  "Refactoring Freelance")],
        d(2025, 6): [("4800.00", "Mission Fintech B — Juin")],
        d(2025, 7): [("4800.00", "Mission Fintech B — Juillet")],
        d(2025, 8): [("2400.00", "Mission Fintech B — partiel (conges)")],
        d(2025, 9): [("5200.00", "Mission Fintech B — Sept"), ("900.00", "Code review freelance")],
        d(2025,10): [("5200.00", "Mission Fintech B — Oct")],
        d(2025,11): [("5200.00", "Mission Fintech B — Nov")],
        d(2025,12): [("5200.00", "Mission Fintech B — Dec"), ("2000.00", "Bonus fin de mission")],
        d(2026, 1): [("4600.00", "Mission Scale-up C — Jan")],
        d(2026, 2): [("4600.00", "Mission Scale-up C — Fev")],
        d(2026, 3): [("4600.00", "Mission Scale-up C — Mars")],
    }

    for mo in THO_MONTHS:
        yr, mth = mo.year, mo.month
        seq = 1

        def tx(acc, day, amount, kind, cat, subcat=None, label=None, tid=None):
            nonlocal seq
            rows.append(TransactionRow(
                id=str(uuid4()), account_id=acc,
                day=day, sequence=seq, amount=amount, currency="EUR",
                kind=kind, category=cat, subcategory=subcat,
                label=label, created_at=now, transfer_id=tid,
                profile_id=THO_PROFILE_ID,
            ))
            seq += 1

        # Revenus freelance
        for i, (amt, label) in enumerate(revenus_freelance.get(mo, [])):
            tx(THO_CHQ, d(yr, mth, 8 + i), Decimal(amt),
               "INCOME", "Revenus", "Freelance", label)

        # Charges URSSAF (trimestriel)
        if mth in (4, 7, 10, 1):
            tx(THO_CHQ, d(yr, mth, 20), -jitter(1100, 0.05),
               "EXPENSE", "Charges", "URSSAF", "Cotisations sociales trimestre")

        # Loyer colocation
        tx(THO_CHQ, d(yr, mth, 1), Decimal("-750.00"),
           "EXPENSE", "Logement", "Loyer", "Loyer colocation")

        # Courses
        tx(THO_CHQ, d(yr, mth, 14), -jitter(180, 0.20),
           "EXPENSE", "Alimentation", "Courses", "Courses Monop")

        # Restaurant / UberEats
        tx(THO_CHQ, d(yr, mth, 22), -jitter(160, 0.30),
           "EXPENSE", "Alimentation", "Restaurant", "Restos / livraisons")

        # Transport (velo + metro occasionnel)
        tx(THO_CHQ, d(yr, mth, 5), -jitter(40, 0.30),
           "EXPENSE", "Transport", "Transports en commun", "Metro ponctuel")

        # Abonnements tech (GitHub, Cloud, etc.)
        tx(THO_CHQ, d(yr, mth, 10), Decimal("-82.00"),
           "EXPENSE", "Loisirs", "Abonnements", "GitHub Pro / AWS / Figma")

        # Materiel informatique (2x/an)
        if mth in (3, 9):
            tx(THO_CHQ, d(yr, mth, 15), -jitter(350, 0.40),
               "EXPENSE", "Materiel", "Informatique", "Achat materiel dev")

        # Sport (salle de sport)
        tx(THO_CHQ, d(yr, mth, 5), Decimal("-45.00"),
           "EXPENSE", "Sante", "Sport", "Abonnement salle CrossFit")

        # Virement vers livret A
        tid_la = str(uuid4())
        la_amount = Decimal("500.00") if mth % 2 == 0 else Decimal("300.00")
        tx(THO_CHQ, d(yr, mth, 25), -la_amount,
           "TRANSFER", "Virement", "Epargne", "Virement Livret A", tid_la)
        la_seq = sum(1 for r in rows if r.account_id == THO_SAV_LA and r.day == d(yr, mth, 25)) + 1
        rows.append(TransactionRow(
            id=str(uuid4()), account_id=THO_SAV_LA,
            day=d(yr, mth, 25), sequence=la_seq, amount=la_amount, currency="EUR",
            kind="TRANSFER", category="Virement", subcategory="Epargne",
            label="Virement depuis Boursorama", created_at=now,
            transfer_id=tid_la, profile_id=THO_PROFILE_ID,
        ))

        seq = 1

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} transactions Thomas inserees.")


# ─────────────────────────────────────────────────────────────────────────────
# Thomas — Portefeuille CTO Trade Republic
# ─────────────────────────────────────────────────────────────────────────────
def _seed_thomas_portfolio(s) -> None:
    from app.repositories.sql_portfolio_repository import PortfolioRow

    print("[seed_demo] Portefeuille Thomas...")
    s.add(PortfolioRow(
        id=str(PF_THO_CTO_UUID), name="CTO Trade Republic",
        currency="EUR", portfolio_type="CTO",
        opened_on=d(2025, 2, 1),
        cash_account_id=PF_THO_CTO_CASH,
        profile_id=THO_PROFILE_ID,
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Thomas — Trades (profil plus concentre : NVDA + MSFT + CW8)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_thomas_trades(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_trade_repository import TradeRow

    print("[seed_demo] Trades Thomas...")
    rows = []

    def t(date, side, sym, qty, price, fees, label=None):
        rows.append(TradeRow(
            id=str(uuid4()), portfolio_id=str(PF_THO_CTO_UUID),
            day=date, side=side, instrument_symbol=sym,
            quantity=Decimal(qty), price=Decimal(price), fees=Decimal(fees),
            currency="EUR", label=label,
            trade_type="TRADE", linked_cash_tx_id=None,
            profile_id=THO_PROFILE_ID,
        ))

    # Thomas arrive tard mais mise fort sur NVDA et les valeurs tech en EUR
    t(d(2025, 2,  5), "BUY",  "NVDA",   "5",  "118.00", "1.00", "Achat NVDA x5 (debut position)")
    t(d(2025, 2, 20), "BUY",  "CW8.PA", "8",  "445.00", "1.99", "Achat CW8 x8")
    t(d(2025, 3, 10), "BUY",  "NVDA",   "5",  "112.00", "1.00", "Renforcement NVDA x5")
    t(d(2025, 4, 15), "BUY",  "MSFT",   "3",  "385.00", "1.00", "Achat Microsoft x3")
    t(d(2025, 5, 20), "SELL", "NVDA",   "3",  "135.00", "1.00", "Vente partielle NVDA (+14%)")
    t(d(2025, 6, 10), "BUY",  "CW8.PA", "5",  "458.00", "1.99", "Renforcement CW8 x5")
    t(d(2025, 7, 15), "BUY",  "NVDA",   "4",  "128.00", "1.00", "Rachat NVDA x4")
    t(d(2025, 9,  5), "BUY",  "MSFT",   "2",  "410.00", "1.00", "Renforcement Microsoft x2")
    t(d(2025,11, 10), "BUY",  "CW8.PA", "5",  "470.00", "1.99", "Renforcement CW8 x5")
    t(d(2026, 1, 20), "BUY",  "NVDA",   "3",  "145.00", "1.00", "Renforcement NVDA x3")
    t(d(2026, 2, 15), "SELL", "NVDA",   "5",  "158.00", "1.00", "Vente partielle NVDA (+23%)")

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} trades Thomas inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Thomas — Snapshots
# ─────────────────────────────────────────────────────────────────────────────
def _seed_thomas_snapshots(s) -> None:
    from uuid import uuid4
    from app.repositories.sql_portfolio_snapshot_repository import PortfolioSnapshotRow

    print("[seed_demo] Snapshots Thomas...")
    rows = []

    vals = _curve(THO_MONTHS, 590, [
        (d(2025, 2),  590),  (d(2025, 2), 3560),
        (d(2025, 3),  560),  (d(2025, 4), 1155),
        (d(2025, 5), -405),  (d(2025, 6), 2290),
        (d(2025, 7),  512),  (d(2025, 9),  820),
        (d(2025,11), 2350),  (d(2026, 1),  435),
        (d(2026, 2), -790),
    ], 0.010, 0.028)

    for mo, v in zip(THO_MONTHS, vals):
        rows.append(PortfolioSnapshotRow(
            id=str(uuid4()), portfolio_id=str(PF_THO_CTO_UUID),
            day=mo, value=Decimal(f"{max(v,0):.2f}"), currency="EUR",
            profile_id=THO_PROFILE_ID,
        ))

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} snapshots Thomas inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Taux de change (EUR comme base, convention : 1 EUR = X devise)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_exchange_rates(s) -> None:
    from app.repositories.sql_exchange_rate_repository import ExchangeRateRow

    print("[seed_demo] Taux de change...")
    now = utcnow()
    # Taux approximatifs courants (1 EUR = X)
    rates = {
        "EUR":  "1.000000",
        "USD":  "1.085000",
        "GBP":  "0.855000",
        "CHF":  "0.960000",
        "JPY":  "161.500000",
        "CAD":  "1.480000",
        "AUD":  "1.650000",
        "SGD":  "1.450000",
        "BTC":  "0.000011",   # 1 EUR ≈ 0.000011 BTC (1 BTC ≈ 91 000 EUR)
        "ETH":  "0.000370",   # 1 EUR ≈ 0.000370 ETH (1 ETH ≈ 2 700 EUR)
        "USDT": "1.085000",
    }
    for currency, rate in rates.items():
        s.add(ExchangeRateRow(
            currency=currency,
            rate=Decimal(rate),
            updated_at=now,
        ))
    print(f"[seed_demo]   {len(rates)} taux inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Prix historiques (partagés entre les deux users)
# ─────────────────────────────────────────────────────────────────────────────
def _seed_prices(s) -> None:
    from app.repositories.sql_price_repository import PricePointRow

    print("[seed_demo] Prix historiques...")
    rows = []
    captured = utcnow()
    random.seed(99)

    curves = {
        "MC.PA":    ("EUR", 648.0,  0.003, 0.020),
        "TTE.PA":   ("EUR", 51.5,   0.004, 0.022),
        "AIR.PA":   ("EUR", 112.0,  0.010, 0.025),
        "BNP.PA":   ("EUR", 56.8,   0.003, 0.020),
        "CW8.PA":   ("EUR", 378.0,  0.007, 0.018),
        "PAEEM.PA": ("EUR", 44.2,   0.003, 0.020),
        "AAPL":     ("EUR", 150.0,  0.009, 0.025),   # prix en EUR (Degiro France)
        "MSFT":     ("EUR", 273.0,  0.010, 0.022),   # prix en EUR (Degiro France)
        "NVDA":     ("EUR", 95.0,   0.020, 0.040),
        "BTC-EUR":  ("EUR", 41000,  0.012, 0.120),
        "ETH-EUR":  ("EUR", 3100,   0.008, 0.110),
    }

    for symbol, (cur, start, drift, vol) in curves.items():
        price = start
        for mo in LEA_MONTHS:  # LEA_MONTHS couvre toute la plage
            ret = drift + random.gauss(0, vol)
            if d(2022,4) <= mo <= d(2022,11) and symbol in ("BTC-EUR", "ETH-EUR"):
                ret -= 0.08
            price = max(price * (1 + ret), 0.01)
            rows.append(PricePointRow(
                symbol=symbol, day=mo,
                price=Decimal(f"{price:.4f}"),
                currency=cur, source="seed_demo", captured_at=captured,
            ))

    for row in rows:
        s.add(row)
    print(f"[seed_demo]   {len(rows)} prix inseres.")


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaire courbe portefeuille
# ─────────────────────────────────────────────────────────────────────────────
def _curve(
    months, initial, purchases, drift, vol,
    bear=None, bear_factor=0.0,
):
    pm = {mo: amt for mo, amt in purchases}
    value = initial
    out = []
    for mo in months:
        value += pm.get(mo, 0)
        ret = drift + random.gauss(0, vol)
        if bear and bear[0] <= mo <= bear[1]:
            ret += bear_factor
        value = max(value * (1 + ret), 0)
        out.append(value)
    return out


if __name__ == "__main__":
    main()
