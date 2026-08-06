"""
Database Test Suite
Tests database connection, models, and queries
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message, level="INFO"):
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}.get(level, RESET)
    print(f"{color}[{level}]{RESET} {message}")


def test_database_connection():
    """Test database connection"""
    log("\n" + "="*60, "INFO")
    log("Testing Database Connection", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        
        with engine.connect() as conn:
            result = conn.execute("SELECT version()").fetchone()
            log(f"✓ Connected to database", "SUCCESS")
            log(f"PostgreSQL version: {result[0][:50]}", "INFO")
            return True
            
    except Exception as e:
        log(f"✗ Database connection failed: {e}", "ERROR")
        return False


def test_pgvector_extension():
    """Test pgvector extension"""
    log("\n" + "="*60, "INFO")
    log("Testing pgvector Extension", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        
        with engine.connect() as conn:
            result = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
            
            if result:
                log(f"✓ pgvector extension installed", "SUCCESS")
                log(f"Version: {result[0]}", "INFO")
                return True
            else:
                log("✗ pgvector extension not found", "ERROR")
                return False
            
    except Exception as e:
        log(f"✗ pgvector check failed: {e}", "ERROR")
        return False


def test_tables_exist():
    """Test if all tables exist"""
    log("\n" + "="*60, "INFO")
    log("Testing Database Tables", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        
        expected_tables = ['users', 'otps', 'items', 'bills', 'sale_items', 'customers']
        
        with engine.connect() as conn:
            result = conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
            
            existing_tables = [row[0] for row in result]
            
            all_exist = True
            for table in expected_tables:
                if table in existing_tables:
                    log(f"✓ Table '{table}' exists", "SUCCESS")
                else:
                    log(f"✗ Table '{table}' missing", "ERROR")
                    all_exist = False
            
            return all_exist
            
    except Exception as e:
        log(f"✗ Table check failed: {e}", "ERROR")
        return False


def test_create_user():
    """Test user creation"""
    log("\n" + "="*60, "INFO")
    log("Testing User Model", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import get_session
        from db.models import User
        from sqlmodel import select
        
        session = next(get_session())
        
        # Check if test user exists
        test_phone = "+919999999998"
        stmt = select(User).where(User.phone_number == test_phone)
        existing = session.exec(stmt).first()
        
        if existing:
            log(f"Test user already exists: ID {existing.id}", "INFO")
            session.close()
            return True
        
        # Create test user
        user = User(
            phone_number=test_phone,
            shop_name="Test Shop",
            owner_name="Test Owner",
            address="Test Address",
            shop_category="Kirana"
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        log(f"✓ User created: ID {user.id}", "SUCCESS")
        log(f"Phone: {user.phone_number}", "INFO")
        log(f"Shop: {user.shop_name}", "INFO")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ User creation failed: {e}", "ERROR")
        return False


def test_create_item():
    """Test item creation"""
    log("\n" + "="*60, "INFO")
    log("Testing Item Model", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import get_session
        from db.models import Item, User
        from sqlmodel import select
        import json
        
        session = next(get_session())
        
        # Get first user
        user = session.exec(select(User)).first()
        if not user:
            log("✗ No user found to create item", "ERROR")
            return False
        
        # Create test item
        item = Item(
            master_id="test-db-001",
            names=json.dumps(["Test Sugar", "टेस्ट चीनी"]),
            category="Grocery",
            price=50.0,
            unit="kg",
            owner_id=user.id
        )
        
        session.add(item)
        session.commit()
        session.refresh(item)
        
        log(f"✓ Item created: ID {item.id}", "SUCCESS")
        log(f"Master ID: {item.master_id}", "INFO")
        log(f"Price: ₹{item.price}", "INFO")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ Item creation failed: {e}", "ERROR")
        return False


def test_vector_search():
    """Test vector similarity search"""
    log("\n" + "="*60, "INFO")
    log("Testing Vector Search", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        from sqlmodel import text
        
        # Create a test vector
        test_vector = [0.1] * 768
        
        with engine.connect() as conn:
            # Test cosine distance
            query = text("""
                SELECT '[0.1]'::vector <=> '[0.2]'::vector as distance
            """)
            result = conn.execute(query).fetchone()
            
            log(f"✓ Vector operations working", "SUCCESS")
            log(f"Test distance: {result[0]}", "INFO")
            return True
            
    except Exception as e:
        log(f"✗ Vector search failed: {e}", "ERROR")
        return False


def test_item_search():
    """Test item search by user"""
    log("\n" + "="*60, "INFO")
    log("Testing Item Search", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import get_session
        from db.models import Item, User
        from sqlmodel import select
        
        session = next(get_session())
        
        # Get first user
        user = session.exec(select(User)).first()
        if not user:
            log("✗ No user found", "ERROR")
            return False
        
        # Search items
        stmt = select(Item).where(Item.owner_id == user.id)
        items = session.exec(stmt).all()
        
        log(f"✓ Found {len(items)} items for user {user.id}", "SUCCESS")
        
        for item in items[:3]:
            log(f"  - {item.master_id}: ₹{item.price}", "INFO")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ Item search failed: {e}", "ERROR")
        return False


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DATABASE TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "connection": test_database_connection(),
        "pgvector": test_pgvector_extension(),
        "tables": test_tables_exist(),
        "user_model": test_create_user(),
        "item_model": test_create_item(),
        "vector_search": test_vector_search(),
        "item_search": test_item_search()
    }
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    for name, success in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
        print(f"{name.upper():20} {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
