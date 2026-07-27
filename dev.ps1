# DashMoney - Script de démarrage dev
# Usage: depuis la racine du projet, lance: .\dev.ps1

param(
    [ValidateSet("Desktop", "Postgres")]
    [string]$DataSource = "Desktop"
)

$ROOT = $PSScriptRoot
$BACKEND = "$ROOT\backend"
$FRONTEND = "$ROOT\frontend"

# --- Config ---
$DB_URL = "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney"
$TEST_DB_URL = "postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_test"
$SECRET_KEY = "dashmoney-dev-secret-key-change-in-production-32chars"
$DOCKER_CONTAINER = "dashmoney-postgres"
$DESKTOP_DATA_DIR = Join-Path $env:APPDATA "DashMoney"
$DESKTOP_DB = Join-Path $DESKTOP_DATA_DIR "data.db"
$DESKTOP_SECRET = Join-Path $DESKTOP_DATA_DIR ".secret_key"

Write-Host "=== DashMoney Dev ===" -ForegroundColor Cyan

# 1. Source de données
if ($DataSource -eq "Postgres") {
    Write-Host "> Demarrage Postgres..." -ForegroundColor Yellow
    docker start $DOCKER_CONTAINER | Out-Null
    Start-Sleep -Seconds 1

    $pg_ok = Test-NetConnection localhost -Port 5432 -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
    if (-not $pg_ok.TcpTestSucceeded) {
        Write-Host "ERREUR: Postgres ne repond pas sur le port 5432" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Postgres OK" -ForegroundColor Green

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
} else {
    Write-Host "> Donnees de l'application desktop..." -ForegroundColor Yellow
    if (-not (Test-Path -LiteralPath $DESKTOP_DB)) {
        Write-Host "ERREUR: base desktop introuvable: $DESKTOP_DB" -ForegroundColor Red
        Write-Host "Lance d'abord l'application DashMoney une fois pour initialiser ses donnees." -ForegroundColor DarkGray
        exit 1
    }
    if (-not (Test-Path -LiteralPath $DESKTOP_SECRET)) {
        Write-Host "ERREUR: cle desktop introuvable: $DESKTOP_SECRET" -ForegroundColor Red
        Write-Host "Lance d'abord l'application DashMoney une fois pour initialiser sa session." -ForegroundColor DarkGray
        exit 1
    }
    Write-Host "  Base partagee: $DESKTOP_DB" -ForegroundColor Green
    Write-Host "  Ferme l'application desktop pendant cette session navigateur." -ForegroundColor DarkGray
}

# Refuse un faux demarrage si une ancienne session ou l'application desktop
# occupe deja un des ports du mode navigateur.
$busyPorts = @()
foreach ($port in 8000, 5173) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $busyPorts += $port
    }
}
if ($busyPorts.Count -gt 0) {
    Write-Host "ERREUR: port(s) deja occupe(s): $($busyPorts -join ', ')" -ForegroundColor Red
    Write-Host "Ferme l'application desktop ou lance .\stop.ps1, puis recommence." -ForegroundColor DarkGray
    exit 1
}

# Logs et PID
$BACKEND_LOG = "$ROOT\backend.log"
$FRONTEND_LOG = "$ROOT\frontend.log"
$PID_FILE = "$ROOT\.dev-pids"

# 2. Backend en arriere-plan (fenetre cachee)
Write-Host "> Demarrage backend (port 8000)..." -ForegroundColor Yellow
if ($DataSource -eq "Postgres") {
    $backendCommand = "cd '$BACKEND'; `$env:DASHMONEY_MODE='server'; `$env:DASHMONEY_DATABASE_URL='$DB_URL'; `$env:DASHMONEY_TEST_DATABASE_URL='$TEST_DB_URL'; `$env:DASHMONEY_SECRET_KEY='$SECRET_KEY'; poetry run uvicorn app.api.main:app --reload --port 8000 *> '$BACKEND_LOG'"
} else {
    $backendCommand = "cd '$BACKEND'; `$env:DASHMONEY_MODE='desktop'; Remove-Item Env:DASHMONEY_DATABASE_URL -ErrorAction SilentlyContinue; `$env:DASHMONEY_SECRET_KEY=(Get-Content -LiteralPath '$DESKTOP_SECRET' -Raw).Trim(); poetry run uvicorn app.api.main:app --reload --port 8000 *> '$BACKEND_LOG'"
}
$backendProc = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @("-Command", $backendCommand)

# 3. Frontend en arriere-plan (fenetre cachee)
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
Write-Host "  Donnees  -> $DataSource" -ForegroundColor White
Write-Host ""
Write-Host "Logs : Get-Content $BACKEND_LOG -Wait" -ForegroundColor DarkGray
Write-Host "       Get-Content $FRONTEND_LOG -Wait" -ForegroundColor DarkGray
Write-Host "Stop : .\stop.ps1" -ForegroundColor DarkGray
