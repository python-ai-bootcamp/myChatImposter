param (
    [switch]$prun,
    [switch]$nginx,
    [switch]$help,
    [switch]$killall
)

if ($help) {
    Write-Host "`nUsage: .\scripts\start.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  --prun   : Prune Docker garbage (stopped containers, images, volumes) before starting."
    Write-Host "  --nginx  : Start only the Nginx service (rebuilds it)."
    Write-Host "  --killall: Force stop and remove ALL Docker containers."
    Write-Host "  --help   : Show this help message."
    exit
}

if ($killall) {
    Write-Host "`n=== Killing ALL Docker containers ===" -ForegroundColor Red
    $containers = docker ps -a -q
    if ($containers) {
        docker stop $containers 2>$null
        docker rm $containers 2>$null
        Write-Host "All containers stopped and removed." -ForegroundColor Green
    } else {
        Write-Host "No containers found." -ForegroundColor DarkGray
    }
}

if ($nginx) {
    Write-Host "`n=== Starting Nginx only ===" -ForegroundColor Cyan
    docker compose -p playground up -d --no-deps --build nginx
    exit
}

if ($prun) {
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
} else {
    Write-Host "`n=== Skipping prune (use --prun to enable) ===" -ForegroundColor Yellow
}
Write-Host "`n=== Starting app ===" -ForegroundColor Cyan

# Ensure log directory exists
$logDir = Join-Path $PSScriptRoot "..\log"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "consoleView.log"

# Build and start — redirect all output to log file AND console
# Build and start — redirect all output to log file AND console
docker compose -p playground up --build 2>&1 | Tee-Object -FilePath $logFile
