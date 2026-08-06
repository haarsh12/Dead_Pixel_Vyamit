# Backend Startup Script (Windows PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MyKirana Backend - Starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-Not (Test-Path "venv")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found!" -ForegroundColor Yellow
    Write-Host "Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[INFO] Please edit .env with your configuration" -ForegroundColor Yellow
    Write-Host ""
}

# Activate venv
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

# Check if dependencies are installed
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Green
$packages = pip list
if ($packages -notmatch "fastapi") {
    Write-Host "[WARN] Dependencies not installed!" -ForegroundColor Yellow
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting FastAPI Server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health: http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start server
python main.py
