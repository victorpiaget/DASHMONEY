import datetime as dt
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_database_url, init_db
from app.api.scheduler import start_scheduler, stop_scheduler

log = logging.getLogger(__name__)

from app.api.routes.health import router as health_router
from app.api.routes.net_worth import router as net_worth_router
from app.api.routes.accounts import router as accounts_router
from app.api.routes.account_transactions import router as account_transactions_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.import_csv import router as import_csv_router
from app.api.routes.portfolios import router as portfolios_router
from app.api.routes.net_worth_full import router as net_worth_full_router
from app.api.routes.instruments import router as instruments_router
from app.api.routes.trades import router as trades_router, pos_router as positions_router
from app.api.routes.prices import router as prices_router
from app.api.routes.profiles import router as workspaces_router, profiles_router
from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.import_boursorama import router as import_boursorama_router
from app.api.routes.import_binance import router as import_binance_router
from app.api.routes.transfers import router as transfers_router
from app.api.routes.asset_transfers import router as asset_transfers_router
from app.api.routes.snapshots import router as snapshots_router
from app.api.routes.me import router as me_router
from app.api.routes.exchange_rates import router as exchange_rates_router
from app.api.routes.transactions_global import router as transactions_global_router
from app.api.routes.import_bank import router as import_bank_router
from app.api.routes.budget_envelopes import router as budget_envelopes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Délègue la résolution de l'URL à app.db.get_database_url, qui gère les
    # deux modes : server (URL obligatoire via env) et desktop (défaut SQLite
    # ~/.dashmoney/data.db si absente).
    db_url = get_database_url()
    log.info("DASHMONEY_DATABASE_URL = %s", db_url)
    init_db()
    start_scheduler()
    log.info("APScheduler started")
    yield
    stop_scheduler()
    log.info("APScheduler stopped")


app = FastAPI(title="DASHMONEY API", version="0.1.0", lifespan=lifespan)

_default_cors = "http://localhost:5173"
# En mode desktop, la WebView Tauri a une origin du type http(s)://tauri.localhost.
# On autorise les deux variantes pour couvrir les versions Windows / WebView2.
if os.getenv("DASHMONEY_MODE", "server").strip().lower() == "desktop":
    _default_cors += ",http://tauri.localhost,https://tauri.localhost"
_cors_origins = [o.strip() for o in os.getenv("DASHMONEY_CORS_ORIGINS", _default_cors).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(net_worth_router)
app.include_router(accounts_router)
app.include_router(account_transactions_router)
app.include_router(budgets_router)
app.include_router(import_csv_router)
app.include_router(portfolios_router)
app.include_router(net_worth_full_router)
app.include_router(instruments_router)
app.include_router(trades_router)
app.include_router(positions_router)
app.include_router(prices_router)
app.include_router(workspaces_router)
app.include_router(profiles_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(import_boursorama_router)
app.include_router(import_binance_router)
app.include_router(transfers_router)
app.include_router(asset_transfers_router)
app.include_router(snapshots_router)
app.include_router(me_router)
app.include_router(exchange_rates_router)
app.include_router(transactions_global_router)
app.include_router(import_bank_router)
app.include_router(budget_envelopes_router)