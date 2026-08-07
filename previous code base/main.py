import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import create_db_and_tables
from app.api import auth, items, voice, voice_inventory, sms_share, analytics, rag_voice

# Conditional RAG admin import - gracefully handle missing numpy/torch
try:
    from app.api import rag_admin
    RAG_ADMIN_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] RAG admin features unavailable: {e}")
    print("[INFO] Install requirements-rag.txt to enable RAG admin features")
    RAG_ADMIN_AVAILABLE = False
    rag_admin = None

# NOTE: vector_search and sequential_llm disabled to save memory

# CORS - allow frontend to call API (set FRONTEND_URL in Render for production)
ALLOWED_ORIGINS = os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
for origin in ["http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"]:
    if origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(origin)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Checking database connection...")
    try:
        create_db_and_tables()
        print("[OK] Database connected successfully.")
    except Exception as e:
        print(f"[WARN] Database connection failed: {str(e)[:100]}")
        print("[WARN] Server will start but database operations will fail.")
        print("[TIP] See DATABASE_CONNECTION_FIX.md or set DATABASE_URL in the host environment.")
    
    # Vector Search Service - DISABLED for 512MB RAM deployments
    print("[INFO] Vector search disabled to conserve memory (512MB limit)")
    print("[TIP] Upgrade to 1GB+ RAM plan to enable ML-based vector search")
    
    yield
    print("Shutdown: Closing connections...")

app = FastAPI(lifespan=lifespan, title="SnapBill API", version="1.0.0")

# CORS middleware - Allow all origins for mobile app (production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(items.router, prefix="/items", tags=["Inventory"])
app.include_router(voice.router, prefix="/voice", tags=["Voice AI"])
app.include_router(voice_inventory.router, prefix="/inventory", tags=["Voice Inventory"])
app.include_router(sms_share.router, prefix="/sms", tags=["SMS Sharing"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Dashboard"])
app.include_router(rag_voice.router, prefix="/rag", tags=["RAG Voice AI - Production"])

# Conditionally include RAG admin router if available
if RAG_ADMIN_AVAILABLE:
    app.include_router(rag_admin.router, prefix="/rag/admin", tags=["RAG Admin & Maintenance"])
    print("[OK] RAG Admin endpoints enabled")
else:
    print("[INFO] RAG Admin endpoints disabled (install requirements-rag.txt to enable)")

# vector_search and sequential_llm routers disabled (memory optimization)

@app.get("/")
def root():
    return {"status": "active", "system": "SnapBill Backend"}


@app.get("/health")
def health_check():
    """Load balancer / Render health check (no DB probe — keeps checks fast)."""
    return {"status": "ok"}