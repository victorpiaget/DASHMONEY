from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from app.settings import get_settings


def _default_sqlite_url() -> str:
    # fallback dev: backend/data/dashmoney.db
    settings = get_settings()
    db_path = settings.data_dir / "dashmoney.db"
    return f"sqlite:///{db_path.as_posix()}"


def get_database_url() -> str:
    env = os.getenv("DASHMONEY_DATABASE_URL")
    if env and env.strip():
        return env.strip()
    return _default_sqlite_url()


@lru_cache
def get_engine() -> Engine:
    url = get_database_url()

    # sqlite needs check_same_thread for FastAPI sync access
    connect_args = {}
    if url.startswith("sqlite:///"):
        connect_args = {"check_same_thread": False}

    return create_engine(url, future=True, connect_args=connect_args)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def new_session() -> Session:
    return get_session_factory()()


def init_db() -> None:
    # import here to avoid circular imports
    from app.repositories.sql_price_repository import Base  # noqa

    engine = get_engine()
    Base.metadata.create_all(engine)