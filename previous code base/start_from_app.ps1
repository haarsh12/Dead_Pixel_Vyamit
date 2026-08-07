# Start server from app directory
cd ..
& ".\venv\Scripts\Activate.ps1"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload