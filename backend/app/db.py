from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


from app.db_base import Base





def get_database_url() -> str:
    env = os.getenv("DASHMONEY_DATABASE_URL", "").strip()
    if not env:
        raise RuntimeError("DASHMONEY_DATABASE_URL is required (SQL-only mode).")
    return env


@lru_cache
def get_engine() -> Engine:
    url = get_database_url()
    return create_engine(url, future=True)


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
