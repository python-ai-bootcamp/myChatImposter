# Startup script: prune Docker garbage, then build and start
# Safely preserves mongo-data volume

Write-Host "`n=== Pruning Docker garbage ===" -ForegroundColor Cyan

# Prune dangling images, stopped containers, build cache (never touches volumes)
docker system prune -af 2>$null

# Prune only non-mongo volumes
$volumes = docker volume ls -q 2>$null
foreach ($vol in $volumes) {
    if ($vol -and $vol -notlike "*mongo*") {
        docker volume rm $vol 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Removed volume: $vol" -ForegroundColor DarkGray
        }
    }
}

Write-Host "=== Prune complete ===" -ForegroundColor Green
Write-Host "`n=== Starting app ===" -ForegroundColor Cyan

# Ensure log directory exists
$logDir = Join-Path $PSScriptRoot "..\log"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "consoleView.log"

# Build and start — redirect all output to log file AND console
docker compose up --build 2>&1 | Tee-Object -FilePath $logFile
