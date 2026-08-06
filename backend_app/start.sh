#!/bin/bash
# Backend Startup Script (Linux/Mac)

echo "========================================"
echo "MyKirana Backend - Starting..."
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Run: python -m venv venv"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[WARN] .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "[INFO] Please edit .env with your configuration"
    echo ""
fi

# Activate venv
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "[INFO] Checking dependencies..."
if ! pip list | grep -q fastapi; then
    echo "[WARN] Dependencies not installed!"
    echo "[INFO] Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "========================================"
echo "Starting FastAPI Server..."
echo "========================================"
echo ""
echo "API Docs: http://localhost:8000/docs"
echo "Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
python main.py
