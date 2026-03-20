# DashMoney - Script de demarrage demo
# Lance l'API sur la DB de demonstration (dashmoney_demo) et le frontend sur le port 5174
# Usage : depuis la racine du projet, lance: .\dev-demo.ps1

$ROOT     = $PSScriptRoot
$BACKEND  = "$ROOT\backend"
$FRONTEND = "$ROOT\frontend"

# --- Config demo ---
$DEMO_DB_URL   = "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_demo"
$SECRET_KEY    = "demo-secret-key-not-for-production-32ch"
$BACKEND_PORT  = 8001
$FRONTEND_PORT = 5174
$DOCKER_CONTAINER = "dashmoney-postgres"

Write-Host ""
Write-Host "=== DashMoney DEMO ===" -ForegroundColor Magenta
Write-Host "  Base    : dashmoney_demo" -ForegroundColor Gray
Write-Host "  Lea     : lea@dashmoney.app     / Demo1234!" -ForegroundColor Gray
Write-Host "  Thomas  : thomas@dashmoney.app  / Demo1234!" -ForegroundColor Gray
Write-Host ""

# 1. Docker Postgres
Write-Host "> Demarrage Postgres..." -ForegroundColor Yellow
docker start $DOCKER_CONTAINER | Out-Null
Start-Sleep -Seconds 1

$pg_ok = Test-NetConnection localhost -Port 5432 -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
if (-not $pg_ok.TcpTestSucceeded) {
    Write-Host "ERREUR: Postgres ne repond pas sur le port 5432" -ForegroundColor Red
    exit 1
}
Write-Host "  Postgres OK" -ForegroundColor Green

# 2. Verifier que la DB demo existe — la creer si absente
Write-Host "> Verification base demo..." -ForegroundColor Yellow
$env:DASHMONEY_DATABASE_URL = $DEMO_DB_URL
$env:DASHMONEY_SECRET_KEY   = $SECRET_KEY

# Verifie l'existence via Python (psycopg deja installe dans le venv)
$checkScript = [System.IO.Path]::GetTempFileName() + ".py"
@"
import psycopg, sys
try:
    conn = psycopg.connect('postgresql://dashmoney:dashmoney@localhost:5432/postgres', autocommit=True)
    row = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'dashmoney_demo'").fetchone()
    print('EXISTS' if row else 'MISSING')
    conn.close()
except Exception:
    print('MISSING')
"@ | Set-Content $checkScript -Encoding UTF8

Push-Location $BACKEND
$db_exists = (poetry run python $checkScript 2>$null)
Pop-Location
Remove-Item $checkScript -ErrorAction SilentlyContinue

if ($db_exists -ne "EXISTS") {
    Write-Host "  Base demo absente - lancement du seed..." -ForegroundColor Yellow
    Push-Location $BACKEND
    poetry run python scripts/seed_demo.py
    Pop-Location
} else {
    Write-Host "  Base demo OK (donnees existantes conservees)" -ForegroundColor Green
}

# 3. Backend demo dans un nouveau terminal (port 8001)
Write-Host "> Demarrage backend demo (port $BACKEND_PORT)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$BACKEND'; `$env:DASHMONEY_DATABASE_URL='$DEMO_DB_URL'; `$env:DASHMONEY_SECRET_KEY='$SECRET_KEY'; Write-Host '--- Backend DEMO (port $BACKEND_PORT) ---' -ForegroundColor Magenta; poetry run uvicorn app.api.main:app --reload --port $BACKEND_PORT"
)

# 5. Frontend dans un nouveau terminal (port 5174, proxy vers backend 8001)
Write-Host "> Demarrage frontend demo (port $FRONTEND_PORT -> backend :$BACKEND_PORT)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$FRONTEND'; `$env:VITE_PROXY_TARGET='http://localhost:$BACKEND_PORT'; Write-Host '--- Frontend DEMO (port $FRONTEND_PORT) ---' -ForegroundColor Magenta; npm run dev -- --port $FRONTEND_PORT"
)

Write-Host ""
Write-Host "Demo lance !" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Backend  -> http://localhost:$BACKEND_PORT/docs" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:$FRONTEND_PORT" -ForegroundColor White
Write-Host ""
Write-Host "  Comptes demo :" -ForegroundColor Cyan
Write-Host "    lea@dashmoney.app    / Demo1234!" -ForegroundColor Gray
Write-Host "    thomas@dashmoney.app / Demo1234!" -ForegroundColor Gray
Write-Host ""
Write-Host "  Pour reseed les donnees :" -ForegroundColor Cyan
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    poetry run python scripts/seed_demo.py" -ForegroundColor Gray
