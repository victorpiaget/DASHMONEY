# DashMoney - Script de démarrage dev
# Usage: depuis la racine du projet, lance: .\dev.ps1

$ROOT = $PSScriptRoot
$BACKEND = "$ROOT\backend"
$FRONTEND = "$ROOT\frontend"

# --- Config ---
$DB_URL = "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney"
$TEST_DB_URL = "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_test"
$SECRET_KEY = "dashmoney-dev-secret-key-change-in-production-32chars"
$DOCKER_CONTAINER = "dashmoney-postgres"

Write-Host "=== DashMoney Dev ===" -ForegroundColor Cyan

# 1. Docker
Write-Host "> Demarrage Postgres..." -ForegroundColor Yellow
docker start $DOCKER_CONTAINER | Out-Null
Start-Sleep -Seconds 1

# Vérifie que Postgres répond
$pg_ok = Test-NetConnection localhost -Port 5432 -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
if (-not $pg_ok.TcpTestSucceeded) {
    Write-Host "ERREUR: Postgres ne repond pas sur le port 5432" -ForegroundColor Red
    exit 1
}
Write-Host "  Postgres OK" -ForegroundColor Green

# 2. Backend dans un nouveau terminal
Write-Host "> Demarrage backend (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$BACKEND'; `$env:DASHMONEY_DATABASE_URL='$DB_URL'; `$env:DASHMONEY_TEST_DATABASE_URL='$TEST_DB_URL'; `$env:DASHMONEY_SECRET_KEY='$SECRET_KEY'; poetry run uvicorn app.api.main:app --reload --port 8000"
)

# 3. Frontend dans un nouveau terminal
Write-Host "> Demarrage frontend (port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$FRONTEND'; npm run dev"
)

Write-Host ""
Write-Host "Tout est lance !" -ForegroundColor Green
Write-Host "  Backend  -> http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:5173" -ForegroundColor White
