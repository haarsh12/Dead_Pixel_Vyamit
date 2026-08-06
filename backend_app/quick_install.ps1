Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Dependencies in venv..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv is activated
if ($env:VIRTUAL_ENV) {
    Write-Host "[OK] Virtual environment is activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual environment not activated!" -ForegroundColor Red
    Write-Host "Run: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Installing packages..." -ForegroundColor Yellow
Write-Host ""

pip install -r requirements.txt

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now run:" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "Or:" -ForegroundColor Yellow
Write-Host "  uvicorn main:app --reload" -ForegroundColor White
Write-Host ""
