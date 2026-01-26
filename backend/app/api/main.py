from fastapi import FastAPI
from app.api.routes.health import router as health_router
from app.api.routes.net_worth import router as net_worth_router
from app.api.site import router as site_router
from app.api.page_tableau_transactions import router as tx_page_router
from app.api.routes.transactions import router as transactions_router
from app.api.routes.accounts import router as accounts_router
from app.api.page_account_transactions import router as account_tx_ui_router
from app.api.routes.import_csv import router as import_csv_router
from app.api.routes.import_victor import router as import_victor_router

app = FastAPI(title="DASHMONEY API", version="0.1.0")

app.include_router(health_router)
app.include_router(net_worth_router)
app.include_router(site_router)
app.include_router(tx_page_router)
app.include_router(transactions_router)
app.include_router(accounts_router)
app.include_router(account_tx_ui_router)
app.include_router(import_csv_router)
app.include_router(import_victor_router)