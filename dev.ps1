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

# 2. Migrations
Write-Host "> Migrations Alembic..." -ForegroundColor Yellow
$env:DASHMONEY_DATABASE_URL = $DB_URL
Push-Location $BACKEND
poetry run alembic upgrade head | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: alembic upgrade head a echoue" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "  Migrations OK" -ForegroundColor Green

# Logs et PID
$BACKEND_LOG = "$ROOT\backend.log"
$FRONTEND_LOG = "$ROOT\frontend.log"
$PID_FILE = "$ROOT\.dev-pids"

# 3. Backend en arriere-plan (fenetre cachee)
Write-Host "> Demarrage backend (port 8000)..." -ForegroundColor Yellow
$backendProc = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
    "-Command",
    "cd '$BACKEND'; `$env:DASHMONEY_DATABASE_URL='$DB_URL'; `$env:DASHMONEY_TEST_DATABASE_URL='$TEST_DB_URL'; `$env:DASHMONEY_SECRET_KEY='$SECRET_KEY'; poetry run uvicorn app.api.main:app --reload --port 8000 *> '$BACKEND_LOG'"
)

# 4. Frontend en arriere-plan (fenetre cachee)
Write-Host "> Demarrage frontend (port 5173)..." -ForegroundColor Yellow
$frontendProc = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
    "-Command",
    "cd '$FRONTEND'; npm run dev *> '$FRONTEND_LOG'"
)

# Sauvegarde des PID pour stop.ps1
"$($backendProc.Id)`n$($frontendProc.Id)" | Out-File -FilePath $PID_FILE -Encoding utf8

Write-Host ""
Write-Host "Tout est lance !" -ForegroundColor Green
Write-Host "  Backend  -> http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Logs : Get-Content $BACKEND_LOG -Wait" -ForegroundColor DarkGray
Write-Host "       Get-Content $FRONTEND_LOG -Wait" -ForegroundColor DarkGray
Write-Host "Stop : .\stop.ps1" -ForegroundColor DarkGray
