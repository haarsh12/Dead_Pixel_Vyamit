# TODO: Complete Backend Implementation

## ✅ Completed

- [x] Clean project structure
- [x] Environment configuration (.env)
- [x] Database models with pgvector
- [x] Security and JWT authentication
- [x] OTP service (secure, tested)
- [x] SMS service (Fast2SMS integration)
- [x] Embedding pipeline (Gemini only)
- [x] Retrieval pipeline (vector search)
- [x] Prompt pipeline (context building)
- [x] LLM pipeline (Mistral + Gemini fallback)
- [x] Authentication API (complete)
- [x] Main application setup
- [x] Documentation (README, SETUP_GUIDE)
- [x] requirements.txt
- [x] .gitignore

## 🔄 In Progress / TODO

### 1. Items API (`api/items.py`)

Copy and adapt from `previous codebase/app/api/items.py`:

```python
# Endpoints to implement:
- GET /items - List user's inventory
- POST /items - Add new item
- PUT /items/{id} - Update item
- DELETE /items/{id} - Delete item
- POST /items/bulk-embed - Generate embeddings for all items
```

**Key changes**:
- Use `from db.models import Item`
- Use `from pipeline.embedding_pipeline import embedding_pipeline`
- Update embedding to use Gemini (768D)
- Use proper error handling

### 2. Analytics API (`api/analytics.py`)

Copy and adapt from `previous codebase/app/api/analytics.py`:

```python
# Endpoints to implement:
- GET /analytics/overview - Dashboard summary
- GET /analytics/top-items - Best selling items
- GET /analytics/peak-hours - Sales by hour
- GET /analytics/category-breakdown - Sales by category
```

**Key changes**:
- Use `from pipeline.retrieval_pipeline import RetrievalPipeline`
- Clean SQL queries
- Add proper date filtering

### 3. RAG Voice AI (`api/rag.py`)

Create new clean implementation inspired by `previous codebase/app/api/rag_voice.py`:

```python
# Endpoints to implement:
- POST /rag/query - Process voice query with RAG
- WS /rag/stream - WebSocket streaming responses (optional)
```

**Implementation**:
```python
from pipeline.embedding_pipeline import embedding_pipeline
from pipeline.retrieval_pipeline import RetrievalPipeline
from pipeline.prompt_pipeline import PromptPipeline
from pipeline.llm_pipeline import llm_pipeline

@router.post("/query")
async def rag_query(request: VoiceQueryRequest, user_id: int = Depends(get_current_user)):
    # 1. Generate query embedding
    query_embedding, _ = embedding_pipeline.generate_query_embedding(request.query)
    
    # 2. Retrieve context
    retrieval = RetrievalPipeline(engine)
    context = await retrieval.retrieve_all_parallel(
        query_embedding,
        user_id,
        request.include_analytics,
        request.include_customers
    )
    
    # 3. Build prompt
    prompt = PromptPipeline.build_rag_prompt(
        request.query,
        context['items'],
        context['analytics'],
        context['customers'],
        shop_category="General"
    )
    
    # 4. Get LLM response
    response, duration, model = llm_pipeline.invoke(prompt)
    
    return response
```

### 4. Embedding Generation Service

Create `services/embedding_service.py`:

```python
# Functions needed:
- generate_item_embeddings(session, user_id) - Embed all items
- generate_customer_embeddings(session, user_id) - Embed customers
- update_single_embedding(session, item_id) - Update one item
```

### 5. Bill Management API (`api/bills.py`)

Copy from `previous codebase`:

```python
# Endpoints:
- POST /bills - Create bill
- GET /bills - List bills
- GET /bills/{id} - Get bill details
- POST /bills/{id}/sms - Send bill via SMS
```

### 6. SMS Share (`api/sms_share.py`)

Copy from `previous codebase/app/api/sms_share.py`:

```python
# Endpoint:
- POST /sms/send-bill - Format and send bill via SMS
```

## 📋 Detailed Migration Steps

### For Each API File:

1. **Copy file from previous codebase**
2. **Update imports**:
   ```python
   # Old
   from app.db.models import Item
   from app.services.otp_service import OTPService
   
   # New
   from db.models import Item
   from services.otp_service import otp_service
   ```

3. **Update embedding calls**:
   ```python
   # Old
   from app.pipeline.embedding_provider import embedding_pipeline
   # embedding_pipeline might be E5 local
   
   # New
   from pipeline.embedding_pipeline import embedding_pipeline
   # Always Gemini, 768D
   ```

4. **Fix vector search queries**:
   ```python
   # Update dimension if needed (768D for Gemini)
   # Update similarity operators (pgvector)
   ```

5. **Add proper error handling**:
   ```python
   try:
       # operation
   except Exception as e:
       logger.error(f"Operation failed: {e}")
       raise HTTPException(...)
   ```

6. **Test endpoint in /docs**

7. **Register in main.py**:
   ```python
   from api import auth, items, analytics, rag
   app.include_router(items.router, prefix="/items", tags=["Inventory"])
   ```

## 🧪 Testing Checklist

After implementing each API:

- [ ] Test in `/docs` interactive API
- [ ] Test authentication flow
- [ ] Test with invalid data
- [ ] Test with missing auth
- [ ] Check error messages
- [ ] Verify database changes
- [ ] Check logs for errors

## 🚀 Deployment Checklist

Before deploying:

- [ ] All endpoints implemented
- [ ] All tests passing
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] Error handling comprehensive
- [ ] Logging properly configured
- [ ] CORS configured correctly
- [ ] Health endpoint working
- [ ] README updated

## 📊 Performance Optimization (Future)

- [ ] Add Redis caching for embeddings
- [ ] Implement connection pooling
- [ ] Add request rate limiting
- [ ] Optimize vector search queries
- [ ] Add batch processing for embeddings
- [ ] Monitor query performance
- [ ] Add database indexes where needed

## 🔒 Security Enhancements (Future)

- [ ] Add rate limiting per user
- [ ] Implement refresh tokens
- [ ] Add API key authentication option
- [ ] Audit logging for sensitive operations
- [ ] Input validation middleware
- [ ] SQL injection prevention review
- [ ] XSS prevention review

## 📝 Documentation (Future)

- [ ] Add API examples for each endpoint
- [ ] Create Postman collection
- [ ] Add architecture diagrams
- [ ] Document deployment process
- [ ] Create troubleshooting guide
- [ ] Add performance tuning guide

## Priority Order

1. **High Priority** (Core functionality):
   - Items API
   - RAG Voice AI
   - Embedding generation service

2. **Medium Priority** (Important features):
   - Bill management
   - Analytics API
   - SMS sharing

3. **Low Priority** (Enhancements):
   - Performance optimization
   - Advanced analytics
   - Additional features

---

## Quick Reference: Files to Copy

From `previous codebase/app/api/`:
- `items.py` → Adapt for new structure
- `analytics.py` → Adapt for new structure
- `rag_voice.py` → Completely rewrite using new pipelines
- `sms_share.py` → Minor updates needed

From `previous codebase/app/services/`:
- `voice_inventory_service.py` → May need adaptation
- Most other services are already reimplemented

**Note**: Don't copy:
- `vector_search_service.py` - Replaced by retrieval_pipeline
- `ai_service*.py` - Replaced by pipeline architecture
- `sequential_multi_llm_service.py` - Not needed

---

**Estimated Time**: 
- Items API: 2 hours
- RAG API: 3 hours
- Analytics API: 2 hours
- Testing & debugging: 2 hours
- **Total**: ~9 hours

**Status**: Core architecture complete (60%), APIs todo (40%)
