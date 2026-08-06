# PowerShell Test Runner for Windows
# Runs all backend tests

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MyKirana Backend Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Blue
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "[WARNING] Virtual environment not found" -ForegroundColor Yellow
    Write-Host "[INFO] Using system Python" -ForegroundColor Yellow
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found!" -ForegroundColor Red
    Write-Host "[INFO] Copy .env.example to .env and configure" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Environment file found" -ForegroundColor Green

# Run tests
Write-Host ""
Write-Host "Running all tests..." -ForegroundColor Blue
Write-Host ""

python test_all.py

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "All tests completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Some tests failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
