"""
RAG Admin API - Pipeline Management & Maintenance
Endpoints for managing embeddings, syncing data, and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session
from sqlalchemy import create_engine
import os

from app.db.database import get_session
from app.db.models import User
from app.core.security import jwt, SECRET_KEY, ALGORITHM

# Conditional RAG imports - gracefully handle missing dependencies
try:
    from app.services.vector_search_service import vector_search_service
    from app.pipeline.customer_pipeline import CustomerPipeline
    from app.pipeline.orchestrator import orchestrator
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] RAG features unavailable: {e}")
    print("[INFO] Install requirements-rag.txt to enable RAG features")
    RAG_AVAILABLE = False
    vector_search_service = None
    CustomerPipeline = None
    orchestrator = None


router = APIRouter()
security = HTTPBearer()


# ===== AUTH HELPER =====

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> tuple:
    """Get current user from JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return int(user_id), user
        
    except Exception as e:
        print(f"[ERROR] Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


# ===== ENDPOINTS =====

@router.get("/pipeline-status")
async def get_pipeline_status(
    user_context: tuple = Depends(get_current_user)
):
    """
    Get comprehensive pipeline status
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="RAG features not available. Install requirements-rag.txt to enable."
        )
    
    try:
        # Orchestrator status
        orch_status = orchestrator.get_status()
        
        # Item embedding stats
        item_stats = vector_search_service.get_embedding_stats()
        
        # Customer embedding stats
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        customer_pipeline = CustomerPipeline(engine)
        customer_stats = customer_pipeline.get_customer_stats()
        
        return {
            "success": True,
            "orchestrator": orch_status,
            "item_embeddings": item_stats,
            "customer_embeddings": customer_stats
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-item-embeddings")
async def sync_item_embeddings(
    user_context: tuple = Depends(get_current_user)
):
    """
    Generate/update embeddings for all items
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="RAG features not available. Install requirements-rag.txt to enable."
        )
    
    user_id, user = user_context
    
    try:
        print(f"[INFO] Starting item embedding sync for user {user_id}")
        
        # Get current stats
        stats_before = vector_search_service.get_embedding_stats()
        
        # Generate embeddings
        result = vector_search_service.embed_all_items(batch_size=50)
        
        # Get updated stats
        stats_after = vector_search_service.get_embedding_stats()
        
        return {
            "success": result['success'],
            "message": result.get('message', ''),
            "before": stats_before,
            "after": stats_after,
            "embedded_items": result.get('embedded_items', 0),
            "failed_items": result.get('failed_items', 0)
        }
        
    except Exception as e:
        print(f"[ERROR] Item embedding sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-customer-embeddings")
async def sync_customer_embeddings(
    user_context: tuple = Depends(get_current_user)
):
    """
    Generate/update embeddings for all customers
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="RAG features not available. Install requirements-rag.txt to enable."
        )
    
    user_id, user = user_context
    
    try:
        print(f"[INFO] Starting customer embedding sync for user {user_id}")
        
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        customer_pipeline = CustomerPipeline(engine)
        
        # Get stats before
        stats_before = customer_pipeline.get_customer_stats(user_id)
        
        # Sync customers
        result = customer_pipeline.sync_customer_embeddings(user_id)
        
        # Get stats after
        stats_after = customer_pipeline.get_customer_stats(user_id)
        
        return {
            "success": result['success'],
            "before": stats_before,
            "after": stats_after,
            "customers_processed": result['customers_processed'],
            "embeddings_created": result['embeddings_created'],
            "embeddings_updated": result['embeddings_updated'],
            "errors": result['errors'],
            "time": result['time']
        }
        
    except Exception as e:
        print(f"[ERROR] Customer embedding sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedding-stats")
async def get_embedding_stats(
    user_context: tuple = Depends(get_current_user)
):
    """
    Get embedding statistics for current user
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="RAG features not available. Install requirements-rag.txt to enable."
        )
    
    user_id, user = user_context
    
    try:
        # Item stats (global)
        item_stats = vector_search_service.get_embedding_stats()
        
        # Customer stats (user-specific)
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        customer_pipeline = CustomerPipeline(engine)
        customer_stats = customer_pipeline.get_customer_stats(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "items": item_stats,
            "customers": customer_stats
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-retrieval")
async def test_retrieval(
    query: str,
    user_context: tuple = Depends(get_current_user)
):
    """
    Test retrieval without invoking LLM
    Returns raw context data
    """
    user_id, user = user_context
    
    try:
        from app.pipeline.embedding_pipeline import embedding_pipeline
        from app.pipeline.retrieval_pipeline import RetrievalPipeline
        
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Generate embedding
        query_embedding, embed_time = embedding_pipeline.generate_query_embedding(query)
        
        # Create retrieval pipeline
        retrieval = RetrievalPipeline(engine, embedding_pipeline)
        
        # Retrieve items
        items, item_time = retrieval.retrieve_items(query_embedding, user_id)
        
        # Retrieve analytics
        analytics, analytics_time = retrieval.retrieve_analytics(user_id)
        
        # Retrieve customers
        customers, customer_time = retrieval.retrieve_customers(query_embedding, user_id)
        
        return {
            "success": True,
            "query": query,
            "timings": {
                "embedding": embed_time,
                "items": item_time,
                "analytics": analytics_time,
                "customers": customer_time
            },
            "results": {
                "items": items,
                "analytics": analytics,
                "customers": customers
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Test retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild-indexes")
async def rebuild_indexes(
    user_context: tuple = Depends(get_current_user)
):
    """
    Rebuild vector indexes for better performance
    (Advanced maintenance)
    """
    user_id, user = user_context
    
    try:
        from sqlalchemy import text
        
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Rebuild item index
            print("[INFO] Rebuilding item vector index...")
            conn.execute(text("DROP INDEX IF EXISTS item_embedding_idx"))
            conn.execute(text("""
                CREATE INDEX item_embedding_idx 
                ON item USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """))
            
            # Rebuild customer index
            print("[INFO] Rebuilding customer vector index...")
            conn.execute(text("DROP INDEX IF EXISTS idx_customer_embedding_vector"))
            conn.execute(text("""
                CREATE INDEX idx_customer_embedding_vector 
                ON customer_embedding 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """))
            
            conn.commit()
        
        return {
            "success": True,
            "message": "Vector indexes rebuilt successfully"
        }
        
    except Exception as e:
        print(f"[ERROR] Index rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check")
async def pipeline_health_check():
    """
    Public health check endpoint (no auth required)
    """
    try:
        # Check embedding model
        from app.pipeline.embedding_pipeline import embedding_pipeline
        model_info = embedding_pipeline.get_model_info()
        
        # Check database
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "embedding_model": model_info['status'],
            "database": "connected",
            "pipeline": "ready"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
