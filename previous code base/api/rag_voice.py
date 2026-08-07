"""
RAG Voice API - Production-Grade Voice AI with RAG Pipeline
Uses the new RAG pipeline for intelligent context-aware responses
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlmodel import Session
import asyncio

from app.db.database import get_session
from app.db.models import User
from app.core.security import jwt, SECRET_KEY, ALGORITHM
from app.pipeline.orchestrator import orchestrator


router = APIRouter()
security = HTTPBearer()


# ===== SCHEMAS =====

class RAGVoiceRequest(BaseModel):
    """Request for RAG voice processing"""
    query: str
    include_analytics: bool = True
    include_customers: bool = True
    use_simple_prompt: bool = False


class RAGVoiceResponse(BaseModel):
    """Response from RAG voice processing"""
    success: bool
    response: Dict[str, Any]
    metadata: Dict[str, Any]


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
        
        # Get user from database
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return int(user_id), user.shop_category or "General"
        
    except Exception as e:
        print(f"[ERROR] Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


# ===== ENDPOINTS =====

@router.post("/process", response_model=RAGVoiceResponse)
async def process_rag_voice(
    request: RAGVoiceRequest,
    user_context: tuple = Depends(get_current_user)
):
    """
    Process voice query using RAG pipeline
    
    Flow:
    1. User speaks → Speech-to-text (handled by frontend/voice service)
    2. Text query arrives here
    3. RAG pipeline:
       - Generate query embedding
       - Retrieve relevant items (PGVector)
       - Calculate analytics metrics
       - Retrieve customer history (if relevant)
       - Build structured prompt
       - Send to LLM (Mistral → Gemini fallback)
    4. Return response
    
    This endpoint replaces the old voice processing logic with the new
    production-grade RAG pipeline.
    """
    
    user_id, shop_category = user_context
    
    try:
        print(f"\n[RAG VOICE API] Processing query from user {user_id}")
        print(f"[RAG VOICE API] Query: \"{request.query}\"")
        print(f"[RAG VOICE API] Shop: {shop_category}")
        
        # Process through RAG pipeline
        result = await orchestrator.process_query(
            user_query=request.query,
            user_id=user_id,
            shop_category=shop_category,
            include_analytics=request.include_analytics,
            include_customers=request.include_customers,
            use_simple_prompt=request.use_simple_prompt
        )
        
        return RAGVoiceResponse(**result)
        
    except Exception as e:
        print(f"[ERROR] RAG voice processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}"
        )


@router.get("/status")
async def get_rag_status(
    user_context: tuple = Depends(get_current_user)
):
    """
    Get RAG pipeline status
    """
    try:
        status = orchestrator.get_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/test")
async def test_rag_pipeline(
    request: RAGVoiceRequest,
    user_context: tuple = Depends(get_current_user)
):
    """
    Test RAG pipeline with detailed debugging
    Same as /process but returns full metadata for testing
    """
    
    user_id, shop_category = user_context
    
    try:
        result = await orchestrator.process_query(
            user_query=request.query,
            user_id=user_id,
            shop_category=shop_category,
            include_analytics=request.include_analytics,
            include_customers=request.include_customers,
            use_simple_prompt=request.use_simple_prompt
        )
        
        # Return everything for debugging
        return {
            "success": result['success'],
            "response": result['response'],
            "metadata": result['metadata'],
            "orchestrator_status": orchestrator.get_status()
        }
        
    except Exception as e:
        print(f"[ERROR] RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )

