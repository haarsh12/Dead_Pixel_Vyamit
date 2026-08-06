"""Database integration checks that leave no records behind."""

import json
import uuid

from dotenv import load_dotenv
from sqlalchemy import text
from sqlmodel import Session, select

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message: str, level: str = "INFO") -> None:
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}[level]
    print(f"{color}[{level}]{RESET} {message}")


def test_database_connection() -> bool:
    try:
        from db.database import engine

        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
        log("Database connection succeeded", "SUCCESS")
        log(f"PostgreSQL: {version[:50]}")
        return True
    except Exception as exc:
        log(f"Database connection failed: {exc}", "ERROR")
        return False


def test_pgvector_extension() -> bool:
    try:
        from db.database import engine

        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
        if version is None:
            log("pgvector extension is not installed", "ERROR")
            return False
        log(f"pgvector extension installed (v{version})", "SUCCESS")
        return True
    except Exception as exc:
        log(f"pgvector check failed: {exc}", "ERROR")
        return False


def test_tables_exist() -> bool:
    expected = {"users", "otps", "items", "bills", "sale_items", "customers"}
    try:
        from db.database import engine

        with engine.connect() as connection:
            actual = set(
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
        missing = sorted(expected - actual)
        if missing:
            log(f"Missing tables: {', '.join(missing)}", "ERROR")
            return False
        log("All required tables exist", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Table check failed: {exc}", "ERROR")
        return False


def test_models_rollback_cleanly() -> bool:
    """Validate ORM models in one transaction, then explicitly roll it back."""
    try:
        from db.database import engine
        from db.models import Item, User

        unique = uuid.uuid4().hex[:12]
        with Session(engine) as session:
            user = User(
                phone_number=f"+91{unique[:10]}",
                shop_name="Database Test Shop",
                owner_name="Database Test Owner",
                address="Temporary test record",
                shop_category="Kirana",
            )
            session.add(user)
            session.flush()

            item = Item(
                master_id=f"test-db-{unique}",
                names=json.dumps(["Test Sugar", "टेस्ट चीनी"], ensure_ascii=False),
                category="Grocery",
                price=50.0,
                unit="kg",
                owner_id=user.id,
            )
            session.add(item)
            session.flush()

            persisted = session.exec(
                select(Item).where(Item.master_id == item.master_id)
            ).one()
            if persisted.owner_id != user.id or persisted.price != 50.0:
                log("Model persistence returned unexpected data", "ERROR")
                session.rollback()
                return False

            session.rollback()

        log("User and item models persist correctly and rollback cleanly", "SUCCESS")
        return True
    except Exception as exc:
        log(f"ORM model check failed: {exc}", "ERROR")
        return False


def test_vector_operations() -> bool:
    try:
        from db.database import engine

        with engine.connect() as connection:
            distance = connection.execute(
                text("SELECT '[0.1,0.2]'::vector <=> '[0.1,0.2]'::vector")
            ).scalar_one()
        if float(distance) != 0.0:
            log(f"Unexpected identical-vector distance: {distance}", "ERROR")
            return False
        log("pgvector cosine-distance operations work", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Vector operation check failed: {exc}", "ERROR")
        return False


def main() -> bool:
    print(f"\n{BLUE}{'=' * 60}{RESET}\n{BLUE}DATABASE TEST SUITE{RESET}\n{BLUE}{'=' * 60}{RESET}")
    results = {
        "connection": test_database_connection(),
        "pgvector": test_pgvector_extension(),
        "tables": test_tables_exist(),
        "models": test_models_rollback_cleanly(),
        "vector_operations": test_vector_operations(),
    }
    print(f"\n{BLUE}{'=' * 60}{RESET}\n{BLUE}TEST SUMMARY{RESET}\n{BLUE}{'=' * 60}{RESET}")
    for name, success in results.items():
        log(f"{name.upper():20} {'PASS' if success else 'FAIL'}", "SUCCESS" if success else "ERROR")
    print(f"\nTotal: {sum(results.values())}/{len(results)} passed")
    return all(results.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
