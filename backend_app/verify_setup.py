"""
Setup Verification Script
Run this to check if everything is configured correctly
"""
import os
import sys

def check_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def success(msg):
    print(f"✅ {msg}")

def warning(msg):
    print(f"⚠️  {msg}")

def error(msg):
    print(f"❌ {msg}")

def info(msg):
    print(f"ℹ️  {msg}")

# Check Python version
check_section("Python Version")
if sys.version_info >= (3, 8):
    success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
else:
    error(f"Python {sys.version_info.major}.{sys.version_info.minor} (need 3.8+)")

# Check .env file
check_section("Environment Configuration")
if os.path.exists(".env"):
    success(".env file exists")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required variables
    required_vars = {
        "DATABASE_URL": "Database connection",
        "SECRET_KEY": "JWT secret key",
        "GEMINI_API_KEY": "Gemini API key"
    }
    
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value and value != f"your_{var.lower()}_here":
            success(f"{var} is set")
        else:
            error(f"{var} is NOT set ({desc})")
    
    # Check optional variables
    optional_vars = {
        "MISTRAL_API_KEY": "Mistral API",
        "FAST2SMS_API_KEY": "SMS service"
    }
    
    for var, desc in optional_vars.items():
        if os.getenv(var):
            success(f"{var} is set")
        else:
            warning(f"{var} not set ({desc} - optional)")
    
else:
    error(".env file not found")
    info("Run: copy .env.example .env (Windows) or cp .env.example .env (Linux/Mac)")

# Check dependencies
check_section("Dependencies")
try:
    import fastapi
    success(f"fastapi v{fastapi.__version__}")
except ImportError:
    error("fastapi not installed")
    info("Run: pip install -r requirements.txt")

try:
    import sqlmodel
    success("sqlmodel installed")
except ImportError:
    error("sqlmodel not installed")

try:
    from google import genai
    success("google-genai installed")
except ImportError:
    error("google-genai not installed")

try:
    import pgvector
    success("pgvector installed")
except ImportError:
    error("pgvector not installed")

# Check file structure
check_section("File Structure")
required_files = [
    "main.py",
    "requirements.txt",
    "api/__init__.py",
    "api/auth.py",
    "api/items.py",
    "api/analytics.py",
    "api/rag.py",
    "api/sms.py",
    "db/models.py",
    "db/database.py",
    "db/schemas.py",
    "core/security.py",
    "services/otp_service.py",
    "services/sms_service.py",
    "pipeline/embedding_pipeline.py",
    "pipeline/retrieval_pipeline.py",
    "pipeline/llm_pipeline.py"
]

for file in required_files:
    if os.path.exists(file):
        success(f"{file}")
    else:
        error(f"{file} missing")

# Test imports
check_section("Import Tests")
try:
    from db.models import User, Item
    success("Database models import OK")
except Exception as e:
    error(f"Database models import failed: {e}")

try:
    from core.security import create_access_token
    success("Security module import OK")
except Exception as e:
    error(f"Security module import failed: {e}")

try:
    from services.otp_service import otp_service
    success("OTP service import OK")
except Exception as e:
    error(f"OTP service import failed: {e}")

try:
    from pipeline.embedding_pipeline import embedding_pipeline
    success("Embedding pipeline import OK")
except Exception as e:
    error(f"Embedding pipeline import failed: {e}")

# Database connection test
check_section("Database Connection")
try:
    from db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        success("Database connection successful")
        
        # Check pgvector
        result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
        if result.fetchone():
            success("pgvector extension enabled")
        else:
            warning("pgvector extension not enabled")
            info("Run in Supabase SQL editor: CREATE EXTENSION IF NOT EXISTS vector;")
            
except Exception as e:
    error(f"Database connection failed: {e}")
    info("Check DATABASE_URL in .env")

# Summary
check_section("Summary")

# Check if key variables need updating
load_dotenv()
needs_update = []
if "YOUR_DATABASE_PASSWORD" in os.getenv("DATABASE_URL", ""):
    needs_update.append("DATABASE_URL (replace YOUR_DATABASE_PASSWORD)")
if os.getenv("SECRET_KEY") == "your-secret-key-generate-with-python-command-above":
    needs_update.append("SECRET_KEY (generate with Python)")
if os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
    needs_update.append("GEMINI_API_KEY (get from Google AI Studio)")

if needs_update:
    print("\n⚠️  IMPORTANT: Update these in .env file:")
    for item in needs_update:
        print(f"   - {item}")
    print("\n📖 See SUPABASE_SETUP.txt for detailed instructions")
else:
    print("\n✅ All configuration looks good!")

print("""
Next steps:
1. If all checks passed, run: python main.py
2. Open: http://localhost:8000/docs
3. Test /health endpoint
4. Try authentication flow

For help, check:
- SUPABASE_SETUP.txt for Supabase configuration
- QUICK_START.txt for quick reference
- BACKEND_COMPLETE.txt for full setup guide
""")

print('='*60)
print("  Verification Complete")
print('='*60 + '\n')
