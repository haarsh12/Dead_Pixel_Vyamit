# Migration Guide: Old → New Backend

## Overview

This guide helps you migrate code from the old backend structure to the new clean architecture.

## Import Changes

### Database

```python
# OLD
from app.db.models import User, Item, Bill
from app.db.database import get_session
from app.db.schemas import ItemCreate

# NEW
from db.models import User, Item, Bill
from db.database import get_session
from db.schemas import ItemCreate
```

### Services

```python
# OLD
from app.services.otp_service import OTPService
otp_service = OTPService()

# NEW
from services.otp_service import otp_service  # Already instantiated
```

### Security

```python
# OLD
from app.core.security import create_access_token, get_current_user

# NEW
from core.security import create_access_token, get_current_user
```

### Embeddings

```python
# OLD
from app.pipeline.embedding_provider import embedding_pipeline
# Could be E5 or Gemini depending on config

# NEW
from pipeline.embedding_pipeline import embedding_pipeline
# Always Gemini, 768D, simplified
```

### Pipeline

```python
# OLD
from app.pipeline.orchestrator import orchestrator
from app.pipeline.retrieval_pipeline import RetrievalPipeline

# NEW
from pipeline.retrieval_pipeline import RetrievalPipeline
from pipeline.prompt_pipeline import PromptPipeline
from pipeline.llm_pipeline import llm_pipeline
from db.database import engine

# Create instances as needed
retrieval = RetrievalPipeline(engine)
```

## Code Pattern Changes

### 1. API Endpoint Structure

**OLD**:
```python
from fastapi import APIRouter, Depends
from app.db.database import get_session
from app.core.security import get_current_user

router = APIRouter()

@router.get("/items")
def get_items(
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user.id  # UserStub object
    # ...
```

**NEW**:
```python
from fastapi import APIRouter, Depends
from db.database import get_session
from core.security import get_current_user

router = APIRouter()

@router.get("/items")
def get_items(
    user_id: int = Depends(get_current_user),  # Direct int
    session: Session = Depends(get_session)
):
    # user_id is already an int
    # ...
```

### 2. Embedding Generation

**OLD**:
```python
from app.pipeline.embedding_provider import embedding_pipeline

# Might be 384D or 768D depending on provider
embedding = embedding_pipeline.generate_embedding(text)
```

**NEW**:
```python
from pipeline.embedding_pipeline import embedding_pipeline, EMBEDDING_DIMENSION

# Always 768D (Gemini)
embedding = embedding_pipeline.generate_embedding(text)
# EMBEDDING_DIMENSION = 768
```

### 3. Vector Search

**OLD**:
```python
# Multiple approaches, inconsistent

# Option 1: Direct SQL
query = text("""
    SELECT *, embedding <-> :embedding as distance
    FROM items
    WHERE owner_id = :user_id
    ORDER BY embedding <-> :embedding
    LIMIT 5
""")

# Option 2: Service layer
from app.services.vector_search_service import vector_search_service
results = vector_search_service.search_items(embedding, user_id)
```

**NEW**:
```python
# Unified approach through retrieval pipeline
from pipeline.retrieval_pipeline import RetrievalPipeline
from db.database import engine

retrieval = RetrievalPipeline(engine)
items = retrieval.retrieve_items(
    query_embedding=embedding,
    user_id=user_id,
    top_k=5,
    threshold=0.3
)
```

### 4. LLM Invocation

**OLD**:
```python
# Multiple services, complex fallback logic
from app.services.ai_service_router import route_ai_request
from app.pipeline.llm_pipeline import LLMPipeline

# Different patterns in different files
```

**NEW**:
```python
# Simple, unified
from pipeline.llm_pipeline import llm_pipeline

response, duration, model_used = llm_pipeline.invoke(prompt)
```

### 5. RAG Query Flow

**OLD** (Complex, scattered):
```python
# Multiple files, unclear flow
from app.pipeline.orchestrator import orchestrator

result = await orchestrator.process_query(
    user_query=query,
    user_id=user_id,
    # many parameters
)
```

**NEW** (Clear, step-by-step):
```python
from pipeline.embedding_pipeline import embedding_pipeline
from pipeline.retrieval_pipeline import RetrievalPipeline
from pipeline.prompt_pipeline import PromptPipeline
from pipeline.llm_pipeline import llm_pipeline
from db.database import engine

# 1. Generate embedding
embedding, _ = embedding_pipeline.generate_query_embedding(query)

# 2. Retrieve context
retrieval = RetrievalPipeline(engine)
context = await retrieval.retrieve_all_parallel(
    query_embedding=embedding,
    user_id=user_id,
    include_analytics=True,
    include_customers=True
)

# 3. Build prompt
prompt = PromptPipeline.build_rag_prompt(
    user_query=query,
    items=context['items'],
    analytics=context['analytics'],
    customers=context['customers'],
    shop_category="General"
)

# 4. Get response
response, duration, model = llm_pipeline.invoke(prompt)
```

## File-by-File Migration

### `items.py`

**Copy from**: `previous codebase/app/api/items.py`

**Changes needed**:
1. Update all imports (remove `app.` prefix)
2. Change `current_user.id` to direct `user_id: int`
3. Update embedding calls to use new pipeline
4. Ensure vector dimension is 768

**Example**:
```python
# OLD
from app.pipeline.embedding_provider import embedding_pipeline
embedding = embedding_pipeline.generate_embedding(item_text)
item.embedding = embedding  # Could be 384D or 768D

# NEW
from pipeline.embedding_pipeline import embedding_pipeline, EMBEDDING_DIMENSION
embedding = embedding_pipeline.generate_embedding(item_text)
item.embedding = embedding  # Always 768D
```

### `analytics.py`

**Copy from**: `previous codebase/app/api/analytics.py`

**Changes needed**:
1. Update imports
2. Use `retrieval.retrieve_analytics()` instead of direct SQL
3. Add proper error handling

**Example**:
```python
# OLD
# Complex SQL queries directly in endpoint

# NEW
from pipeline.retrieval_pipeline import RetrievalPipeline
from db.database import engine

retrieval = RetrievalPipeline(engine)
analytics = retrieval.retrieve_analytics(user_id=user_id, days=30)
```

### `rag_voice.py` → `rag.py`

**Rewrite completely** using new pipeline:

```python
from fastapi import APIRouter, Depends
from db.database import get_session, engine
from db.schemas import VoiceQueryRequest, VoiceQueryResponse
from core.security import get_current_user
from pipeline.embedding_pipeline import embedding_pipeline
from pipeline.retrieval_pipeline import RetrievalPipeline
from pipeline.prompt_pipeline import PromptPipeline
from pipeline.llm_pipeline import llm_pipeline

router = APIRouter()

@router.post("/query", response_model=VoiceQueryResponse)
async def rag_query(
    request: VoiceQueryRequest,
    user_id: int = Depends(get_current_user)
):
    # See example in TODO.md
    pass
```

## Common Migration Patterns

### Pattern 1: Service Initialization

**OLD**:
```python
# Create new instance every time
from app.services.otp_service import OTPService
otp_service = OTPService()
otp_code = otp_service.create_otp(session, phone)
```

**NEW**:
```python
# Use global singleton
from services.otp_service import otp_service
otp_code = otp_service.create_otp(session, phone)
```

### Pattern 2: Error Handling

**OLD**:
```python
@router.get("/items")
def get_items(...):
    items = session.exec(select(Item)).all()
    return items
```

**NEW**:
```python
import logging
logger = logging.getLogger(__name__)

@router.get("/items")
def get_items(...):
    try:
        items = session.exec(select(Item)).all()
        return items
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch items"
        )
```

### Pattern 3: Logging

**OLD**:
```python
print(f"[OK] Something happened")
print(f"[ERROR] Something failed: {e}")
```

**NEW**:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Something happened")
logger.error(f"Something failed: {e}")
```

## Database Changes

### Vector Column

**OLD**:
```python
# Might be 384D
embedding: Optional[list] = Field(default=None, sa_column=Column(Vector(384)))
```

**NEW**:
```python
# Always 768D
embedding: Optional[list] = Field(default=None, sa_column=Column(Vector(768)))
```

**Migration**: If you have existing data with 384D embeddings, you'll need to regenerate them:
```python
# Run once to regenerate all embeddings
from services.embedding_service import generate_item_embeddings
generate_item_embeddings(session, user_id)
```

## Environment Variables

### OLD `.env`:
```env
DATABASE_URL=...
SECRET_KEY=...
EMBEDDING_PROVIDER=1  # or 2
EMBEDDING_MODEL=intfloat/multilingual-e5-small
GEMINI_API_KEY=...
MISTRAL_API_KEY=...
```

### NEW `.env`:
```env
DATABASE_URL=...
SECRET_KEY=...
EMBEDDING_PROVIDER=1  # Always Gemini
GEMINI_API_KEY=...  # Required
MISTRAL_API_KEY=...  # Optional
# EMBEDDING_MODEL removed - always embedding-001
```

## Testing Migration

### 1. Test Imports
```python
# Create test file: test_imports.py
from db.models import User, Item
from db.database import get_session
from services.otp_service import otp_service
from pipeline.embedding_pipeline import embedding_pipeline
from core.security import create_access_token

print("All imports successful!")
```

### 2. Test Embedding
```python
from pipeline.embedding_pipeline import embedding_pipeline

embedding = embedding_pipeline.generate_embedding("test")
assert len(embedding) == 768
print(f"Embedding dimension: {len(embedding)} ✓")
```

### 3. Test Authentication
```bash
curl -X POST http://localhost:8000/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "9876543210", "is_login": false}'
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Remove `app.` prefix from imports
```python
# Wrong
from app.db.models import User

# Right
from db.models import User
```

### Embedding Dimension Mismatch

**Problem**: `embedding dimension 384 doesn't match 768`

**Solution**: Regenerate embeddings with new pipeline

### Current User Type

**Problem**: `'int' object has no attribute 'id'`

**Solution**: `get_current_user` now returns int directly
```python
# OLD
current_user = Depends(get_current_user)
user_id = current_user.id

# NEW
user_id: int = Depends(get_current_user)
```

## Checklist

- [ ] Update all imports (remove `app.` prefix)
- [ ] Change `current_user.id` to `user_id: int`
- [ ] Update embedding pipeline imports
- [ ] Update vector dimensions to 768
- [ ] Add error handling with try/except
- [ ] Replace print() with logger
- [ ] Test each endpoint after migration
- [ ] Update environment variables
- [ ] Regenerate embeddings if needed
- [ ] Test end-to-end flow

## Need Help?

1. Check `TODO.md` for implementation examples
2. Compare with `api/auth.py` (completed example)
3. Review `previous codebase` for original logic
4. Check logs for detailed error messages

---

**Remember**: The new structure is simpler and cleaner. If something seems complicated, there's probably a simpler way in the new architecture.
