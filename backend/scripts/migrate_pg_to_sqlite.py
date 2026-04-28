"""
Migration one-shot Postgres → SQLite pour DashMoney (mode desktop).

Usage typique :
    cd backend
    poetry run python scripts/migrate_pg_to_sqlite.py \\
        --source "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney" \\
        --target "~/.dashmoney/data.db"

Étapes :
    1. Valide que l'URL source est Postgres et que la cible n'existe pas.
    2. Crée le fichier SQLite et son schéma via `Base.metadata.create_all()`
       (les migrations Alembic d'origine sont Postgres-only — elles utilisent
       ALTER TABLE ADD CONSTRAINT, non supporté par SQLite hors batch mode.
       `metadata.create_all` produit un schéma équivalent et est déjà validé
       par les 222 tests d'intégration SQLite).
    3. Stamp Alembic à `head` pour que la base soit considérée à jour.
    4. Copie chaque table dans l'ordre topologique des FK (Base.metadata.sorted_tables)
       avec FK désactivées pendant l'opération.
    5. Lance `PRAGMA foreign_key_check` sur la SQLite finale pour valider l'intégrité.
    6. Affiche un récap des comptes par table.

Ne touche jamais à la source Postgres (lecture seule).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ajoute le root backend au sys.path pour pouvoir importer `app.*`
HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
sys.path.insert(0, str(BACKEND_ROOT))


def _validate_source_url(url: str) -> None:
    if not (url.startswith("postgresql://") or url.startswith("postgresql+")):
        raise SystemExit(
            f"❌ La source doit être une URL Postgres, reçu : {url!r}\n"
            f"   Format attendu : postgresql+psycopg://user:pass@host:port/dbname"
        )


def _resolve_target_path(raw: str) -> Path:
    path = Path(os.path.expanduser(raw)).resolve()
    if path.exists():
        raise SystemExit(
            f"❌ Le fichier SQLite cible existe déjà : {path}\n"
            f"   Supprime-le manuellement (ou choisis un autre chemin) avant de relancer.\n"
            f"   Refus volontaire pour éviter d'écraser des données par accident."
        )
    return path


def _import_all_models() -> None:
    """
    Force l'enregistrement de tous les modèles sur Base.metadata pour que
    `Base.metadata.sorted_tables` soit complet.
    """
    from app.repositories import (  # noqa: F401
        sql_account_repository,
        sql_budget_envelope_repository,
        sql_category_repository,
        sql_exchange_rate_repository,
        sql_identity_models,
        sql_instrument_repository,
        sql_portfolio_repository,
        sql_portfolio_snapshot_repository,
        sql_price_repository,
        sql_trade_repository,
        sql_transaction_repository,
    )


def _create_schema_and_stamp(target_sqlite_url: str) -> None:
    """
    Crée le schéma SQLite via Base.metadata.create_all (les migrations Alembic
    d'origine ne sont pas portables SQLite — elles font des ALTER TABLE ADD
    CONSTRAINT). Puis stamp Alembic à `head` pour que la base soit considérée
    à jour côté Alembic.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    from app.db_base import Base

    engine = create_engine(target_sqlite_url, future=True)
    Base.metadata.create_all(engine)
    engine.dispose()

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    previous = os.environ.get("DASHMONEY_DATABASE_URL")
    os.environ["DASHMONEY_DATABASE_URL"] = target_sqlite_url
    try:
        command.stamp(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("DASHMONEY_DATABASE_URL", None)
        else:
            os.environ["DASHMONEY_DATABASE_URL"] = previous


def _copy_table(table, src_engine, tgt_conn, batch_size: int) -> int:
    """
    Lecture intégrale puis insertion par batch. OK pour DashMoney (volume modeste).
    Pour des bases plus grosses, on streamerait avec yield_per.
    """
    from sqlalchemy import select

    with src_engine.connect() as src_conn:
        rows = src_conn.execute(select(table)).fetchall()

    if not rows:
        return 0

    payload = [dict(row._mapping) for row in rows]
    for start in range(0, len(payload), batch_size):
        chunk = payload[start : start + batch_size]
        tgt_conn.execute(table.insert(), chunk)
    return len(rows)


def _foreign_key_check(tgt_engine) -> list[tuple]:
    with tgt_engine.connect() as conn:
        return list(conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migre les données d'une base DashMoney Postgres vers une SQLite locale.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="URL Postgres source (ex. postgresql+psycopg://user:pass@host:5432/dashmoney).",
    )
    parser.add_argument(
        "--target",
        default="~/.dashmoney/data.db",
        help="Chemin du fichier SQLite cible (défaut : ~/.dashmoney/data.db).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Taille des batches d'insertion (défaut : 1000).",
    )
    args = parser.parse_args()

    source_url = args.source.strip()
    _validate_source_url(source_url)
    target_path = _resolve_target_path(args.target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{target_path.as_posix()}"

    # Imports tardifs (après sys.path)
    from sqlalchemy import create_engine, text

    # ─── 1. Test connexion source ──────────────────────────────────────
    print(f"🔌 Test connexion source ({source_url}) ...")
    src_engine = create_engine(source_url, future=True)
    with src_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("   OK")

    # ─── 2. Création schéma SQLite (metadata.create_all + stamp Alembic) ──
    _import_all_models()
    print(f"🛠️  Création du schéma SQLite sur {target_path} ...")
    _create_schema_and_stamp(sqlite_url)
    print("   OK (alembic stamp head appliqué)")

    from app.db_base import Base

    sorted_tables = list(Base.metadata.sorted_tables)
    skip_tables = {"alembic_version"}

    tgt_engine = create_engine(sqlite_url, future=True)

    # ─── 3. Copie des données ──────────────────────────────────────────
    print("📦 Copie Postgres → SQLite (ordre topologique FK) ...")
    counts: list[tuple[str, int]] = []
    with tgt_engine.begin() as tgt_conn:
        tgt_conn.exec_driver_sql("PRAGMA foreign_keys = OFF")
        for table in sorted_tables:
            if table.name in skip_tables:
                continue
            n = _copy_table(table, src_engine, tgt_conn, args.batch_size)
            counts.append((table.name, n))
            print(f"   • {table.name:<32} {n:>8} rows")
    # FK seront réactivées automatiquement par l'event listener `_enable_sqlite_foreign_keys`
    # à la prochaine connexion de l'app (chaque connection SQLite gère son propre PRAGMA).

    # ─── 4. Vérification d'intégrité ───────────────────────────────────
    print("🔍 PRAGMA foreign_key_check ...")
    violations = _foreign_key_check(tgt_engine)
    if violations:
        print(f"❌ {len(violations)} violation(s) FK détectée(s) :", file=sys.stderr)
        for v in violations[:20]:
            print(f"   {v}", file=sys.stderr)
        if len(violations) > 20:
            print(f"   ... ({len(violations) - 20} de plus)", file=sys.stderr)
        return 2
    print("   OK (0 violation)")

    # ─── 5. Récap ──────────────────────────────────────────────────────
    total = sum(n for _, n in counts)
    print()
    print("✅ Migration terminée")
    print(f"   Cible : {target_path}")
    print(f"   Total : {total} rows copiées sur {len(counts)} tables")
    print()
    print("Pour utiliser cette base :")
    print("   $env:DASHMONEY_MODE = 'desktop'")
    print(f"   $env:DASHMONEY_DATABASE_URL = '{sqlite_url}'")
    print("   poetry run uvicorn app.api.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
