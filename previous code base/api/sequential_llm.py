"""
API endpoints for Sequential Multi-LLM Orchestration System
Hackathon Implementation for Vyamit AI
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio

from ..services.sequential_multi_llm_service import get_sequential_service, SequentialMultiLLMService

router = APIRouter()

# Request/Response Models
class QueryRequest(BaseModel):
    text: str
    include_history: bool = True

class QueryResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    execution_time: float
    confidence_score: Optional[float] = None
    timestamp: str
    conversation_length: int
    error: Optional[str] = None

class ConversationHistory(BaseModel):
    conversations: List[Dict[str, str]]
    total_count: int

class PerformanceStats(BaseModel):
    total_requests: int
    qwen_success: int
    gemini_success: int
    gemma_success: int
    total_failures: int
    avg_response_time: float
    total_logs: int
    memory_conversations: int

@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process user query through Sequential Multi-LLM system
    
    Pipeline: Qwen → Gemini → Gemma with memory and logging
    """
    try:
        service = get_sequential_service()
        result = await service.process_query(request.text)
        
        return QueryResponse(
            success=result["success"],
            response=result["response"],
            model_used=result["model_used"],
            execution_time=result["execution_time"],
            confidence_score=result.get("confidence_score"),
            timestamp=result["timestamp"],
            conversation_length=result.get("conversation_length", 0),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/conversation-history", response_model=ConversationHistory)
async def get_conversation_history():
    """Get complete conversation history from memory"""
    try:
        service = get_sequential_service()
        history = service.get_conversation_history()
        
        return ConversationHistory(
            conversations=history,
            total_count=len(history)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@router.get("/performance-stats", response_model=PerformanceStats)
async def get_performance_stats():
    """Get system performance statistics"""
    try:
        service = get_sequential_service()
        stats = service.get_performance_stats()
        
        return PerformanceStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

@router.get("/recent-logs")
async def get_recent_logs(limit: int = 10):
    """Get recent processing logs"""
    try:
        service = get_sequential_service()
        logs = service.get_recent_logs(limit)
        
        return {
            "logs": logs,
            "count": len(logs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")

@router.post("/clear-memory")
async def clear_conversation_memory():
    """Clear conversation memory"""
    try:
        service = get_sequential_service()
        service.clear_memory()
        
        return {"message": "Conversation memory cleared successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@router.get("/system-info")
async def get_system_info():
    """Get system information and status"""
    try:
        service = get_sequential_service()
        stats = service.get_performance_stats()
        
        return {
            "system_name": "Sequential Multi-LLM Orchestration System with Memory & Logging",
            "version": "1.0.0",
            "models": ["Qwen/Qwen2.5-7B-Instruct", "Gemini-1.5-Flash", "Google/Gemma-2B"],
            "execution_order": ["QWEN", "GEMINI", "GEMMA"],
            "features": [
                "Sequential model execution",
                "Conversation memory",
                "Structured logging",
                "Response validation",
                "Performance tracking"
            ],
            "status": "active",
            "performance": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system info: {str(e)}")

# Test endpoint for hackathon demo
@router.post("/demo-test")
async def demo_test():
    """
    Demo test endpoint for hackathon presentation
    Tests all three models with sample queries
    """
    try:
        service = get_sequential_service()
        
        test_queries = [
            "2 kilo chawal 50 rupaye kilo",
            "What is the price of tomatoes?",
            "Hello, how are you?"
        ]
        
        results = []
        
        for query in test_queries:
            print(f"\n[INFO] DEMO TEST: Processing '{query}'")
            result = await service.process_query(query)
            results.append({
                "query": query,
                "result": result
            })
        
        return {
            "demo_name": "Sequential Multi-LLM Orchestration Demo",
            "test_queries": len(test_queries),
            "results": results,
            "system_performance": service.get_performance_stats()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo test error: {str(e)}")