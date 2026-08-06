# MyKirana Backend - Clean Architecture

## Overview

This is a completely redesigned backend with:
- ✅ Clean, modular architecture
- ✅ Gemini API embeddings (768D) - NO local models
- ✅ Proper security and authentication
- ✅ Supabase PostgreSQL with pgvector
- ✅ Well-structured pipelines
- ✅ Comprehensive error handling
- ✅ Production-ready code

## Architecture

```
backend_app/
├── api/                    # API endpoints
│   ├── auth.py            # Authentication (OTP-based)
│   ├── items.py           # Inventory management (TODO)
│   ├── analytics.py       # Business analytics (TODO)
│   └── rag.py             # RAG voice AI (TODO)
├── core/                  # Core utilities
│   ├── security.py        # JWT authentication
│   └── shop_categories.py # Shop type definitions
├── db/                    # Database layer
│   ├── models.py          # SQLModel models with pgvector
│   ├── database.py        # Connection management
│   └── schemas.py         # Pydantic request/response schemas
├── pipeline/              # RAG pipeline
│   ├── embedding_pipeline.py  # Gemini embeddings
│   ├── retrieval_pipeline.py  # Vector search
│   ├── prompt_pipeline.py     # Prompt building
│   ├── llm_pipeline.py        # Mistral + Gemini LLMs
│   └── config.py              # Pipeline configuration
├── services/              # Business logic
│   ├── otp_service.py     # OTP generation/verification
│   └── sms_service.py     # Fast2SMS integration
├── main.py                # FastAPI application
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
└── README.md             # This file
```

## Quick Start

### 1. Setup Environment

```bash
cd backend_app

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy template
copy .env.example .env

# Edit .env and add your values:
# - DATABASE_URL (Supabase PostgreSQL)
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)
# - MISTRAL_API_KEY (get from https://console.mistral.ai/)
# - FAST2SMS_API_KEY (optional, for SMS)
```

### 3. Setup Database

Your Supabase database needs pgvector extension:

```sql
-- Run this in Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Run Application

```bash
# Development mode (with auto-reload)
python main.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase PostgreSQL URL | `postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| `SECRET_KEY` | JWT signing key | Generate with Python command |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `MISTRAL_API_KEY` | Mistral AI key (primary LLM) | None (uses Gemini) |
| `FAST2SMS_API_KEY` | SMS service key | None (mocked) |
| `OTP_DEMO_MODE` | Always use 112233 as OTP | `0` |
| `LOG_OTP_CODES` | Log OTP to console (debug only) | `0` |
| `DB_ECHO` | Log SQL queries | `0` |
| `FRONTEND_URL` | Allowed CORS origins | `http://localhost:3000` |

## API Endpoints

### Authentication (`/auth`)

- `POST /auth/request-otp` - Request OTP for login/signup
- `POST /auth/verify-otp` - Verify OTP and get JWT token
- `GET /auth/profile` - Get user profile (requires auth)
- `PUT /auth/profile` - Update profile (requires auth)

### TODO: Remaining Endpoints

The following routes need to be implemented by copying and adapting from the previous codebase:

1. **Items API** (`/items`)
   - GET /items - List inventory
   - POST /items - Add item with embedding
   - PUT /items/{id} - Update item
   - DELETE /items/{id} - Delete item
   - POST /items/bulk-embed - Generate embeddings

2. **Analytics API** (`/analytics`)
   - GET /analytics/overview - Dashboard summary
   - GET /analytics/top-items - Best sellers
   - GET /analytics/peak-hours - Sales by time

3. **RAG Voice AI** (`/rag`)
   - POST /rag/query - Voice query with RAG
   - WS /rag/stream - Streaming responses

## Database Models

### User
- Shop owner with authentication
- Fields: phone, shop_name, owner_name, address, shop_category

### Item
- Inventory with multi-language names
- **Vector embedding (768D)** for semantic search
- Fields: master_id, names (JSON), category, price, unit

### Customer
- Customer profiles with purchase history
- **Vector embedding (768D)** for behavior patterns
- Fields: phone, name, total_bills, total_spent

### Bill & SaleItem
- Transaction history
- Fields: items_json, total_amount, customer_info

## Pipeline Flow

### RAG Query Pipeline

```
User Query
    ↓
1. Gemini Embedding (768D)
    ↓
2. Parallel Retrieval
    ├─→ Vector Search (Items)
    ├─→ Vector Search (Customers)
    └─→ Analytics (SQL)
    ↓
3. Prompt Building
    ↓
4. LLM (Mistral → Gemini fallback)
    ↓
5. JSON Response
```

## Security

- **JWT Authentication**: Secure token-based auth
- **OTP Verification**: Phone number verification
- **Password Hashing**: Not needed (OTP-based)
- **Rate Limiting**: TODO - add in production
- **CORS**: Configured for mobile app

## Production Deployment

### Render / Railway

1. Connect GitHub repository
2. Set environment variables in dashboard
3. Use `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Health check: `/health`

### Supabase Database

1. Create new project
2. Get connection string from settings
3. Enable pgvector extension
4. Update `DATABASE_URL` in env

## Development Workflow

### Add New Endpoint

1. Create router in `api/`
2. Define schemas in `db/schemas.py`
3. Import and register in `main.py`
4. Test with `/docs` interactive API

### Add New Service

1. Create service in `services/`
2. Follow singleton pattern
3. Add proper error handling
4. Export in `__init__.py`

## Troubleshooting

### Database Connection Failed
- Check `DATABASE_URL` format
- Ensure pgvector is enabled in Supabase
- Verify network access to database

### Embedding Generation Failed
- Verify `GEMINI_API_KEY` is set
- Check API quota/limits
- Review logs for specific error

### OTP Not Received
- Check `FAST2SMS_API_KEY` is valid
- Use `OTP_DEMO_MODE=1` for testing (OTP: 112233)
- Review SMS service logs

## Migration from Old Backend

### What's Copied (No Changes Needed)
- ✅ OTP Service
- ✅ SMS Service
- ✅ Security/JWT
- ✅ Database models structure
- ✅ Shop categories

### What's Improved
- ✅ Gemini embeddings only (no local models)
- ✅ Clean pipeline architecture
- ✅ Better error handling
- ✅ Proper logging
- ✅ Type hints everywhere
- ✅ Modular structure

### What's Removed
- ❌ Local E5 embedding model
- ❌ Conflicting pipeline logic
- ❌ Messy code structure
- ❌ Redundant services

## Next Steps

1. **Copy Remaining API Routes**: Adapt items, analytics, RAG endpoints from previous codebase
2. **Test All Endpoints**: Use `/docs` to test each route
3. **Add Embedding Generation**: Implement bulk embedding for items
4. **Deploy to Production**: Set up on Render/Railway with Supabase
5. **Monitor and Optimize**: Add logging, monitoring, caching

## Support

For issues or questions:
1. Check logs in console
2. Review `.env` configuration
3. Verify all API keys are valid
4. Test with `/docs` interactive API

---

**Version**: 2.0.0
**Last Updated**: 2026-08-06
**Status**: Core complete, additional routes TODO
