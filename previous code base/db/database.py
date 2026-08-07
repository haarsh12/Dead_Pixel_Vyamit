from sqlmodel import SQLModel, create_engine, Session
from app.db.models import User, OTP, Item
from dotenv import load_dotenv
import os

load_dotenv()

# Get DATABASE_URL from environment (Render sets this)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix for Render/Supabase - use postgresql:// instead of postgres://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine - fail with helpful message if DATABASE_URL not set
if DATABASE_URL is None or DATABASE_URL.strip() == "":
    raise ValueError(
        "DATABASE_URL is not set. "
        "For Render: add DATABASE_URL in Dashboard > Environment. "
        "Create a PostgreSQL database first, then use its Internal Database URL."
    )

# Production: echo=False to reduce log noise. Set DB_ECHO=1 for debugging.
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "0").lower() in ("1", "true", "yes"),
    pool_pre_ping=True,  # Verify connections before use (handles Render DB timeouts)
    pool_recycle=300,    # Recycle connections every 5 min (Render free tier)
)

# 4. Function to create tables (Run this when app starts)
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# 5. Dependency (We use this in every API endpoint to get a DB session)
def get_session():
    with Session(engine) as session:
        yield session