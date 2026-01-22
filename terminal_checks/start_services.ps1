# Text Order Processing System - Service Startup Script
# This script checks which services are running and starts only the ones that aren't

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Text Order Processing System - Service Manager" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Get the project root directory (parent of terminal_checks)
$scriptPath = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $scriptPath

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

# Function to check if a process is running
function Test-Process {
    param([string]$ProcessName)
    $process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    return $null -ne $process
}

# Check Redis
Write-Host "[1/4] Checking Redis Server..." -ForegroundColor Yellow
if (Test-Process "redis-server") {
    Write-Host "  [OK] Redis is already running" -ForegroundColor Green
} else {
    Write-Host "  [X] Redis is not running" -ForegroundColor Red
    Write-Host "  -> Please start Redis manually or install it as a Windows service" -ForegroundColor Yellow
    Write-Host "     Download: https://github.com/tporadowski/redis/releases" -ForegroundColor Gray
}
Write-Host ""

# Check FastAPI Backend
Write-Host "[2/4] Checking FastAPI Backend (port 8000)..." -ForegroundColor Yellow
if (Test-Port 8000) {
    Write-Host "  [OK] FastAPI backend is already running on port 8000" -ForegroundColor Green
    # Test if it's responding
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/" -TimeoutSec 2
        Write-Host "  [OK] Backend is responding: $($response.message)" -ForegroundColor Green
    } catch {
        Write-Host "  [!] Port 8000 is in use but backend is not responding" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [X] FastAPI backend is not running" -ForegroundColor Red
    Write-Host "  -> Starting FastAPI backend..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
    Write-Host "  [OK] FastAPI backend started in new window" -ForegroundColor Green
}
Write-Host ""

# Check Celery Worker
Write-Host "[3/4] Checking Celery Worker..." -ForegroundColor Yellow
if (Test-Process "celery") {
    Write-Host "  [OK] Celery worker is already running" -ForegroundColor Green
} else {
    Write-Host "  [X] Celery worker is not running" -ForegroundColor Red
    Write-Host "  -> Starting Celery worker..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; celery -A backend.celery_app worker --loglevel=info --pool=solo"
    Write-Host "  [OK] Celery worker started in new window" -ForegroundColor Green
}
Write-Host ""

# Check Frontend Dev Server
Write-Host "[4/4] Checking Frontend Dev Server (port 5173)..." -ForegroundColor Yellow
if (Test-Port 5173) {
    Write-Host "  [OK] Frontend dev server is already running on port 5173" -ForegroundColor Green
} else {
    Write-Host "  [X] Frontend dev server is not running" -ForegroundColor Red
    Write-Host "  -> Starting Frontend dev server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\frontend'; npm run dev"
    Write-Host "  [OK] Frontend dev server started in new window" -ForegroundColor Green
}
Write-Host ""

# Wait a moment for services to start
Start-Sleep -Seconds 3

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Service Status Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Final status check
$redisRunning = Test-Process "redis-server"
$backendRunning = Test-Port 8000
$celeryRunning = Test-Process "celery"
$frontendRunning = Test-Port 5173

Write-Host "Redis:      $(if($redisRunning){'[OK] Running'}else{'[X] Not Running'})" -ForegroundColor $(if($redisRunning){'Green'}else{'Red'})
Write-Host "Backend:    $(if($backendRunning){'[OK] Running on http://localhost:8000'}else{'[X] Not Running'})" -ForegroundColor $(if($backendRunning){'Green'}else{'Red'})
Write-Host "Celery:     $(if($celeryRunning){'[OK] Running'}else{'[X] Not Running'})" -ForegroundColor $(if($celeryRunning){'Green'}else{'Red'})
Write-Host "Frontend:   $(if($frontendRunning){'[OK] Running on http://localhost:5173'}else{'[X] Not Running'})" -ForegroundColor $(if($frontendRunning){'Green'}else{'Red'})
Write-Host ""

if ($redisRunning -and $backendRunning -and $celeryRunning -and $frontendRunning) {
    Write-Host "SUCCESS! All services are running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Open your browser and navigate to:" -ForegroundColor Cyan
    Write-Host "  -> http://localhost:5173" -ForegroundColor White -BackgroundColor Blue
    Write-Host ""
} else {
    Write-Host "WARNING: Some services are not running. Please check the output above." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

