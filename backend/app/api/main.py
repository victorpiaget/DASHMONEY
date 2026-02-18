import os

from fastapi import FastAPI

from app.db import init_db

from app.api.routes.health import router as health_router
from app.api.routes.net_worth import router as net_worth_router
from app.api.routes.accounts import router as accounts_router
from app.api.routes.account_transactions import router as account_transactions_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.import_csv import router as import_csv_router
from app.api.routes.import_victor import router as import_victor_router
from app.api.routes.portfolios import router as portfolios_router
from app.api.routes.net_worth_full import router as net_worth_full_router
from app.api.routes.instruments import router as instruments_router
from app.api.routes.trades import router as trades_router, pos_router as positions_router
from app.api.routes.prices import router as prices_router


app = FastAPI(title="DASHMONEY API", version="0.1.0")

@app.on_event("startup")
def _startup_sql_only() -> None:
    db_url = os.getenv("DASHMONEY_DATABASE_URL", "").strip()
    if not db_url:
        raise RuntimeError("DASHMONEY_DATABASE_URL is required (SQL-only mode).")
    # Fail fast if DB unreachable + ensure tables exist
    init_db()

app.include_router(health_router)
app.include_router(net_worth_router)
app.include_router(accounts_router)
app.include_router(account_transactions_router)
app.include_router(budgets_router)
app.include_router(import_csv_router)
app.include_router(import_victor_router)
app.include_router(portfolios_router)
app.include_router(net_worth_full_router)
app.include_router(instruments_router)
app.include_router(trades_router)
app.include_router(positions_router)
app.include_router(prices_router)