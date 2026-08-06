# Quick Installation Script
Write-Host "Installing backend dependencies..." -ForegroundColor Cyan

# Upgrade pip first
python -m pip install --upgrade pip

# Install dependencies
pip install fastapi==0.115.0
pip install uvicorn[standard]==0.32.0
pip install python-multipart==0.0.12
pip install sqlmodel==0.0.22
pip install psycopg2-binary==2.9.9
pip install pgvector==0.3.5
pip install alembic==1.13.3
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install python-dotenv==1.0.1
pip install google-generativeai==0.8.3
pip install mistralai==1.2.3
pip install requests==2.32.3
pip install pydantic==2.9.2
pip install pydantic-settings==2.5.2

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Now run: python main.py" -ForegroundColor Yellow
