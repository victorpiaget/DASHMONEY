# DashMoney - Arret des serveurs lances par dev.ps1
# Usage : .\stop.ps1

$ROOT = $PSScriptRoot
$PID_FILE = "$ROOT\.dev-pids"

Write-Host "=== DashMoney Stop ===" -ForegroundColor Cyan

# 1. Tue les process enregistres dans .dev-pids
if (Test-Path $PID_FILE) {
    $pids = Get-Content $PID_FILE | Where-Object { $_ -match '^\d+$' }
    foreach ($targetPid in $pids) {
        try {
            $proc = Get-Process -Id $targetPid -ErrorAction Stop
            # Tue tout l'arbre (powershell wrapper + uvicorn/node enfants)
            taskkill /PID $targetPid /T /F 2>&1 | Out-Null
            Write-Host "  Process $targetPid (`"$($proc.ProcessName)`") arrete" -ForegroundColor Green
        } catch {
            Write-Host "  Process $targetPid deja arrete" -ForegroundColor DarkGray
        }
    }
    Remove-Item $PID_FILE -Force
} else {
    Write-Host "  Pas de fichier .dev-pids — fallback sur les ports" -ForegroundColor DarkGray
}

# 2. Filet de securite : tue tout ce qui ecoute sur 8000 et 5173
foreach ($port in 8000, 5173) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try {
            taskkill /PID $c.OwningProcess /T /F 2>&1 | Out-Null
            Write-Host "  Port $port libere (PID $($c.OwningProcess))" -ForegroundColor Green
        } catch {}
    }
}

Write-Host "OK" -ForegroundColor Green
