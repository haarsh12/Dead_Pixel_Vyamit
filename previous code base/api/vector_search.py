"""
Vector Search API — RAG-based inventory search with multilingual support.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.vector_search_service import vector_search_service
from app.core.term_logger import log_api_call
import time

router = APIRouter()

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query in any language (Hindi/English/Hinglish)")
    top_k: Optional[int] = Field(15, ge=1, le=50, description="Number of results to return")
    similarity_threshold: Optional[float] = Field(0.1, ge=0.0, le=1.0, description="Minimum similarity threshold")
    debug: Optional[bool] = Field(False, description="Enable debug output")

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_matches: int
    search_time_ms: float
    debug_info: Optional[Dict[str, Any]] = None

class EmbedItemRequest(BaseModel):
    item_id: int
    names: List[str]
    category: str
    unit: str
    price: Optional[float] = 0.0

class EmbedAllResponse(BaseModel):
    success: bool
    message: str
    total_items: int
    embedded_items: int
    failed_items: int
    error: Optional[str] = None

@router.post("/search", response_model=SearchResponse)
async def search_inventory(request: SearchRequest):
    """
    Search inventory using vector similarity.
    """
    start_time = time.time()
    
    try:
        # Validate input
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        log_api_call("POST", "/vector/search", params={"query": request.query, "top_k": request.top_k})

        # Perform vector search using production-ready service
        results = vector_search_service.search_items(
            query=request.query.strip(),
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            debug=request.debug
        )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"🎯 [VECTOR EMBEDDING SEARCH] Found {len(results)} matches using model 'intfloat/multilingual-e5-small' in {search_time:.2f}ms")
        for idx, r in enumerate(results[:3]):
            print(f"   • Match #{idx+1}: {r.get('name')} (Score: {r.get('similarity_score', 0):.4f})")
        
        # Prepare debug info if requested
        debug_info = None
        if request.debug:
            debug_info = {
                "model": "intfloat/multilingual-e5-small",
                "embedding_dimension": 384,
                "similarity_threshold": request.similarity_threshold,
                "query_processed": f"query: {request.query}",
                "search_time_ms": round(search_time, 2)
            }
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_matches=len(results),
            search_time_ms=round(search_time, 2),
            debug_info=debug_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search")
async def search_inventory_get(
    q: str = Query(..., description="Search query in any language"),
    top_k: int = Query(15, ge=1, le=50, description="Number of results to return"),
    threshold: float = Query(0.1, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    debug: bool = Query(False, description="Enable debug output")
):
    """
    Search inventory using GET (easy to test in a browser).
    Example: /vector/search?q=tamatar ka rate&top_k=10&debug=true
    """
    request = SearchRequest(
        query=q,
        top_k=top_k,
        similarity_threshold=threshold,
        debug=debug
    )
    
    return await search_inventory(request)

@router.post("/embed-item")
async def embed_single_item(request: EmbedItemRequest):
    """
    Generate and store embedding for a single item.

    Use when adding new items or updating existing items.
    """
    try:
        item_data = {
            'names': request.names,
            'category': request.category,
            'unit': request.unit,
            'price': request.price or 0.0
        }
        
        success = vector_search_service.update_item_embedding(
            item_id=request.item_id,
            item_data=item_data
        )
        
        if success:
            return {
                "success": True,
                "message": f"Embedding updated for item {request.item_id}",
                "item_data": item_data,
                "model": "intfloat/multilingual-e5-small"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate or store embedding")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@router.post("/embed-all", response_model=EmbedAllResponse)
async def embed_all_items(
    batch_size: int = Query(50, ge=1, le=100, description="Batch size for processing")
):
    """
    Generate embeddings for all items that do not have them yet.

    One-time setup or after bulk imports; processes in batches.
    Processes items in batches for efficiency.
    """
    try:
        result = vector_search_service.embed_all_items(batch_size=batch_size)
        
        return EmbedAllResponse(
            success=result["success"],
            message=result["message"],
            total_items=result["total_items"],
            embedded_items=result["embedded_items"],
            failed_items=result["failed_items"],
            error=result.get("error")
        )
        
    except Exception as e:
        return EmbedAllResponse(
            success=False,
            message="Batch embedding failed",
            total_items=0,
            embedded_items=0,
            failed_items=0,
            error=str(e)
        )

@router.get("/stats")
async def get_embedding_statistics():
    """
    Current embedding statistics (counts and coverage percentage).
    """
    try:
        stats = vector_search_service.get_embedding_stats()
        
        return {
            "embedding_stats": stats,
            "model": "intfloat/multilingual-e5-small",
            "embedding_dimension": 384,
            "recommendations": {
                "coverage_good": stats["coverage_percent"] >= 90,
                "action_needed": "Run /embed-all if coverage < 90%" if stats["coverage_percent"] < 90 else "All good!"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@router.get("/similar/{item_id}")
async def get_similar_items(
    item_id: int,
    top_k: int = Query(5, ge=1, le=20, description="Number of similar items to return")
):
    """
    Find items similar to a given item (recommendations / related products).
    """
    try:
        similar_items = vector_search_service.get_similar_items(
            item_id=item_id,
            top_k=top_k
        )
        
        return {
            "reference_item_id": item_id,
            "similar_items": similar_items,
            "total_found": len(similar_items),
            "model": "intfloat/multilingual-e5-small"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar items search failed: {str(e)}")

@router.get("/test-queries")
async def test_multilingual_queries():
    """
    Run predefined multilingual queries to verify vector search.
    """
    test_queries = [
        "tamatar ka rate kya hai",           # Hinglish - tomato
        "प्याज का भाव बताओ",                # Hindi - onion
        "rice ka price kitna hai",           # Hinglish - rice
        "what is wheat cost",                # English - wheat
        "चीनी का रेट क्या है",               # Hindi - sugar
        "dal moong ka bhav",                 # Hinglish - lentils
        "milk powder price",                 # English - milk powder
        "आटा कितने का है",                   # Hindi - flour
        "oil ka rate batao",                 # Hinglish - oil
        "टोमॅटो किती रुपये"                  # Marathi - tomato
    ]
    
    results = {}
    total_successful = 0
    
    for query in test_queries:
        try:
            search_results = vector_search_service.search_items(
                query=query,
                top_k=5,
                similarity_threshold=0.1
            )
            
            results[query] = {
                "matches": len(search_results),
                "top_match": search_results[0] if search_results else None,
                "status": "success"
            }
            
            if search_results:
                total_successful += 1
                
        except Exception as e:
            results[query] = {
                "error": str(e),
                "status": "failed"
            }
    
    return {
        "test_results": results,
        "summary": {
            "total_queries": len(test_queries),
            "successful_queries": total_successful,
            "success_rate": f"{(total_successful/len(test_queries)*100):.1f}%"
        },
        "model": "intfloat/multilingual-e5-small",
        "embedding_dimension": 384
    }

@router.get("/health")
async def health_check():
    """
    Health check for the vector search service (DB + model + sample query).
    """
    try:
        # Test embedding stats
        stats = vector_search_service.get_embedding_stats()
        
        # Test a simple search
        test_results = vector_search_service.search_items(
            query="test",
            top_k=1,
            similarity_threshold=0.0
        )
        
        return {
            "status": "healthy",
            "model": "intfloat/multilingual-e5-small",
            "embedding_dimension": 384,
            "database_connection": "active",
            "embedding_stats": stats,
            "test_search": "passed" if isinstance(test_results, list) else "failed",
            "service_ready": True
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_ready": False
        }