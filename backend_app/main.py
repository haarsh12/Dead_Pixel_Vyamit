"""
Main Application Entry Point
FastAPI backend with clean architecture
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import database
from db.database import create_db_and_tables

# Import API routers
from api import auth, items, analytics, rag, sms

# CORS configuration
ALLOWED_ORIGINS = os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
# Add local development origins
for origin in ["http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"]:
    if origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(origin)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        create_db_and_tables()
        logger.info("[OK] Database initialized successfully")
    except Exception as e:
        logger.error(f"[ERROR] Database initialization failed: {e}")
        logger.warning("[WARN] Server starting but database operations will fail")
    
    # Initialize embedding pipeline (lazy loading)
    try:
        from pipeline import embedding_pipeline
        logger.info("[OK] Embedding pipeline ready (lazy loading)")
    except Exception as e:
        logger.error(f"[ERROR] Embedding pipeline initialization failed: {e}")
    
    logger.info("=" * 60)
    logger.info("APPLICATION READY")
    logger.info("=" * 60)
    
    yield
    
    logger.info("=" * 60)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="MyKirana Backend API",
    version="2.0.0",
    description="Clean backend architecture with Gemini embeddings and proper pipelines",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for mobile app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(items.router, prefix="/items", tags=["Inventory"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(rag.router, prefix="/rag", tags=["RAG Voice AI"])
app.include_router(sms.router, prefix="/sms", tags=["SMS"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "status": "active",
        "system": "MyKirana Backend",
        "version": "2.0.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers"""
    return {"status": "ok"}


@app.get("/info")
def system_info():
    """System information endpoint"""
    return {
        "version": "2.0.0",
        "embedding_provider": "gemini",
        "embedding_dimension": 768,
        "database": "postgresql+pgvector"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # Disable reload in production (Render), enable in local development
    reload_mode = os.getenv("RENDER") is None
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload_mode
    )