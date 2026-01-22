# Text Order Processing System - Status Checker
# This script checks the status of all services without starting or stopping them

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Text Order Processing System - Status Check" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

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

# Check each service
Write-Host "[1/4] Redis Server" -ForegroundColor Yellow
$redisRunning = Test-Process "redis-server"
if ($redisRunning) {
    $redisProcess = Get-Process -Name "redis-server"
    Write-Host "  Status: [RUNNING]" -ForegroundColor Green
    Write-Host "  PID: $($redisProcess.Id)" -ForegroundColor Gray
    Write-Host "  Memory: $([math]::Round($redisProcess.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "  Status: [NOT RUNNING]" -ForegroundColor Red
}
Write-Host ""

Write-Host "[2/4] FastAPI Backend (Port 8000)" -ForegroundColor Yellow
$backendRunning = Test-Port 8000
if ($backendRunning) {
    $conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "  Status: [RUNNING]" -ForegroundColor Green
    Write-Host "  URL: http://localhost:8000" -ForegroundColor Gray
    Write-Host "  PID: $($process.Id)" -ForegroundColor Gray
    Write-Host "  Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray

    # Test API health
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  Health: [OK] $($response.message)" -ForegroundColor Green
        Write-Host "  Version: $($response.version)" -ForegroundColor Gray
    } catch {
        Write-Host "  Health: [WARNING] API not responding" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Status: [NOT RUNNING]" -ForegroundColor Red
}
Write-Host ""

Write-Host "[3/4] Celery Worker" -ForegroundColor Yellow
$celeryRunning = Test-Process "celery"
if ($celeryRunning) {
    $celeryProcess = Get-Process -Name "celery"
    Write-Host "  Status: [RUNNING]" -ForegroundColor Green
    Write-Host "  PID: $($celeryProcess.Id)" -ForegroundColor Gray
    Write-Host "  Memory: $([math]::Round($celeryProcess.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "  Status: [NOT RUNNING]" -ForegroundColor Red
}
Write-Host ""

Write-Host "[4/4] Frontend Dev Server (Port 5173)" -ForegroundColor Yellow
$frontendRunning = Test-Port 5173
if ($frontendRunning) {
    $conn = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
    $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "  Status: [RUNNING]" -ForegroundColor Green
    Write-Host "  URL: http://localhost:5173" -ForegroundColor Gray
    Write-Host "  PID: $($process.Id)" -ForegroundColor Gray
    Write-Host "  Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "  Status: [NOT RUNNING]" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

$allRunning = $redisRunning -and $backendRunning -and $celeryRunning -and $frontendRunning
$runningCount = @($redisRunning, $backendRunning, $celeryRunning, $frontendRunning).Where({$_}).Count

Write-Host "Services Running: $runningCount/4" -ForegroundColor $(if($allRunning){'Green'}else{'Yellow'})
Write-Host ""

if ($allRunning) {
    Write-Host "[SUCCESS] All services are operational!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to use:" -ForegroundColor Cyan
    Write-Host "  > Frontend: http://localhost:5173" -ForegroundColor White
    Write-Host "  > API Docs: http://localhost:8000/docs" -ForegroundColor White
} elseif ($runningCount -eq 0) {
    Write-Host "[WARNING] No services are running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start all services, run:" -ForegroundColor Cyan
    Write-Host "  > .\start_services.ps1" -ForegroundColor White
} else {
    Write-Host "[WARNING] Some services are not running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start missing services, run:" -ForegroundColor Cyan
    Write-Host "  > .\start_services.ps1" -ForegroundColor White
}
Write-Host ""

# Quick actions menu
Write-Host "Quick Actions:" -ForegroundColor Cyan
Write-Host "  [S] Start services" -ForegroundColor Gray
Write-Host "  [T] Stop services" -ForegroundColor Gray
Write-Host "  [R] Refresh status" -ForegroundColor Gray
Write-Host "  [Q] Quit" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Select an option (S/T/R/Q)"

switch ($choice.ToUpper()) {
    "S" {
        Write-Host ""
        Write-Host "Starting services..." -ForegroundColor Yellow
        & "$PSScriptRoot\start_services.ps1"
    }
    "T" {
        Write-Host ""
        Write-Host "Stopping services..." -ForegroundColor Yellow
        & "$PSScriptRoot\stop_services.ps1"
    }
    "R" {
        Write-Host ""
        Write-Host "Refreshing status..." -ForegroundColor Yellow
        & "$PSScriptRoot\check_status.ps1"
    }
    "Q" {
        Write-Host "Goodbye!" -ForegroundColor Green
    }
    default {
        Write-Host "Invalid option. Exiting." -ForegroundColor Red
    }
}

