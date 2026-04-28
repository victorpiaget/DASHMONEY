from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


from app.db_base import Base


# ---------------------------------------------------------------------------
# Mode (desktop / server)
# ---------------------------------------------------------------------------
# `server` (par défaut) = SaaS web, Postgres requis, URL fournie via env.
# `desktop`             = appli native locale, SQLite par défaut si URL absente.

VALID_MODES = {"server", "desktop"}


def get_mode() -> str:
    mode = os.getenv("DASHMONEY_MODE", "server").strip().lower()
    if mode not in VALID_MODES:
        raise RuntimeError(
            f"DASHMONEY_MODE invalide : {mode!r}. Valeurs autorisées : {sorted(VALID_MODES)}."
        )
    return mode


_LEGACY_DATA_DIR = Path.home() / ".dashmoney"


def default_desktop_data_dir() -> Path:
    """
    Emplacement standard des données DashMoney en mode desktop, selon l'OS :
        - Windows : %APPDATA%/DashMoney  (typiquement C:/Users/<user>/AppData/Roaming/DashMoney)
        - macOS   : ~/Library/Application Support/DashMoney
        - Linux   : $XDG_DATA_HOME/DashMoney  (fallback ~/.local/share/DashMoney)

    Crée le dossier s'il n'existe pas.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA", "")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_DATA_HOME", "")
        root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    data_dir = root / "DashMoney"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def migrate_legacy_data_dir() -> None:
    """
    Migre l'ancien dossier ~/.dashmoney/ vers le nouvel emplacement standard.

    Idempotent : ne fait rien si le nouveau path contient déjà `data.db`,
    ou si l'ancien dossier n'existe pas. Utilise `shutil.move` (atomic
    rename si même volume, copy + delete sinon).
    """
    new_dir = default_desktop_data_dir()
    if not _LEGACY_DATA_DIR.exists() or _LEGACY_DATA_DIR.resolve() == new_dir.resolve():
        return

    legacy_db = _LEGACY_DATA_DIR / "data.db"
    new_db = new_dir / "data.db"
    if legacy_db.exists() and not new_db.exists():
        shutil.move(str(legacy_db), str(new_db))

    # Migre aussi le .secret_key (signe les JWT) pour ne pas invalider les
    # sessions existantes au premier lancement après l'upgrade.
    legacy_secret = _LEGACY_DATA_DIR / ".secret_key"
    new_secret = new_dir / ".secret_key"
    if legacy_secret.exists() and not new_secret.exists():
        shutil.move(str(legacy_secret), str(new_secret))


def _default_desktop_database_url() -> str:
    """
    URL SQLite par défaut pour le mode desktop.

    Calcule le path selon l'OS via `default_desktop_data_dir()` et migre
    automatiquement les données depuis l'ancien `~/.dashmoney/` si
    applicable (transparence pour l'utilisateur qui upgrade).
    """
    migrate_legacy_data_dir()
    db_path = default_desktop_data_dir() / "data.db"
    return f"sqlite:///{db_path}"


def get_database_url() -> str:
    env = os.getenv("DASHMONEY_DATABASE_URL", "").strip()
    if env:
        return env
    if get_mode() == "desktop":
        return _default_desktop_database_url()
    raise RuntimeError(
        "DASHMONEY_DATABASE_URL is required (server mode). "
        "Set DASHMONEY_MODE=desktop pour utiliser une SQLite locale par défaut."
    )


@lru_cache
def get_engine() -> Engine:
    url = get_database_url()
    connect_args: dict = {}
    if url.startswith("sqlite"):
        # SQLite + multi-thread : indispensable pour FastAPI/uvicorn
        connect_args["check_same_thread"] = False
    return create_engine(url, future=True, connect_args=connect_args)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def new_session() -> Session:
    return get_session_factory()()


def init_db() -> None:
    """
    Ensure database connectivity.

    Schema management is handled by Alembic migrations.
    This function MUST NOT create or modify tables.
    """
    engine = get_engine()
    # Simple connectivity check (fail-fast)
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")


# ---------------------------------------------------------------------------
# SQLite : activer les foreign keys (off par défaut sur SQLite, c'est un piège)
# ---------------------------------------------------------------------------

@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
