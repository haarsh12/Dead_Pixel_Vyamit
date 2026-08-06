"""
Database Connection and Session Management
Includes pgvector extension setup
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix Supabase/Render postgres:// to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL or DATABASE_URL.strip() == "":
    raise ValueError(
        "DATABASE_URL not set. Add it to .env file or environment variables. "
        "Format: postgresql://postgres:password@host:port/database"
    )

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "0") in ("1", "true"),
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_size=5,
    max_overflow=10
)


def enable_pgvector():
    """Enable pgvector extension in database"""
    try:
        with Session(engine) as session:
            session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.commit()
            print("[OK] pgvector extension enabled")
    except Exception as e:
        print(f"[WARN] Could not enable pgvector: {e}")
        print("[INFO] Ensure your database supports pgvector extension")


def create_db_and_tables():
    """Create all tables and enable extensions"""
    try:
        # Enable pgvector first
        enable_pgvector()
        
        # Create tables
        SQLModel.metadata.create_all(engine)
        print("[OK] Database tables created successfully")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        raise


def get_session():
    """Dependency for getting database sessions"""
    with Session(engine) as session:
        yield session
