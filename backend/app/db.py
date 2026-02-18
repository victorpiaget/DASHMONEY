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
    from app.repositories.sql_price_repository import PricePointRow
    from app.repositories.sql_account_repository import AccountRow
    from app.repositories.sql_transaction_repository import TransactionRow
    from app.repositories.sql_instrument_repository import InstrumentRow
    from app.repositories.sql_trade_repository import TradeRow
    from app.repositories.sql_portfolio_repository import PortfolioRow
    from app.repositories.sql_portfolio_snapshot_repository import PortfolioSnapshotRow

    engine = get_engine()
    Base.metadata.create_all(engine)
