# Text Order Processing System - Service Shutdown Script
# This script stops all running services

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Text Order Processing System - Service Shutdown" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Function to kill processes on a specific port
function Stop-ProcessOnPort {
    param([int]$Port, [string]$ServiceName)

    Write-Host "Stopping $ServiceName (port $Port)..." -ForegroundColor Yellow

    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  -> Killing process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Gray
                Stop-Process -Id $process.Id -Force
                Write-Host "  [OK] $ServiceName stopped" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  [OK] $ServiceName is not running" -ForegroundColor Green
    }
}

# Function to kill processes by name
function Stop-ProcessByName {
    param([string]$ProcessName, [string]$ServiceName)

    Write-Host "Stopping $ServiceName..." -ForegroundColor Yellow

    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if ($processes) {
        foreach ($proc in $processes) {
            Write-Host "  -> Killing process: $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force
        }
        Write-Host "  [OK] $ServiceName stopped" -ForegroundColor Green
    } else {
        Write-Host "  [OK] $ServiceName is not running" -ForegroundColor Green
    }
}

# Stop services
Write-Host "[1/3] Stopping Frontend Dev Server..." -ForegroundColor Yellow
Stop-ProcessOnPort -Port 5173 -ServiceName "Frontend"
Write-Host ""

Write-Host "[2/3] Stopping FastAPI Backend..." -ForegroundColor Yellow
Stop-ProcessOnPort -Port 8000 -ServiceName "FastAPI Backend"
Write-Host ""

Write-Host "[3/3] Stopping Celery Worker..." -ForegroundColor Yellow
Stop-ProcessByName -ProcessName "celery" -ServiceName "Celery Worker"
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Note: Redis server is left running (if it's a Windows service)" -ForegroundColor Yellow
Write-Host "To stop Redis, run: Stop-Service redis" -ForegroundColor Gray
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[OK] All application services stopped!" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

