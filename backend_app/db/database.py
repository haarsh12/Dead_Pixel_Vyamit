"""
Database Connection and Session Management
Includes pgvector extension setup
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from dotenv import load_dotenv
import os
from typing import Generator, Optional

from fastapi import HTTPException, status

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix Supabase/Render postgres:// to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# A missing database must not prevent health checks, OpenAPI, or deployment
# diagnostics from starting.  Protected routes receive a clear 503 until the
# operator configures DATABASE_URL.
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "10"))
engine = None

if DATABASE_URL and DATABASE_URL.strip():
    # Fail fast when a remote database is unavailable. Without an explicit
    # connect timeout, a DNS/network issue can block a worker indefinitely.
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "0") in ("1", "true"),
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        pool_timeout=DB_POOL_TIMEOUT,
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT},
    )


def database_is_configured() -> bool:
    """Return whether an engine can be opened for protected data operations."""
    return engine is not None


def enable_pgvector():
    """Enable pgvector extension in database"""
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
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
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    try:
        # Enable pgvector first
        enable_pgvector()
        
        # Create tables
        SQLModel.metadata.create_all(engine)
        print("[OK] Database tables created successfully")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions"""
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Set DATABASE_URL and restart the service.",
        )
    with Session(engine) as session:
        yield session
