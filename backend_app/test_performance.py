"""
Performance Benchmark Tests
Tests response times and throughput
"""
import os
import time
import statistics
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


def benchmark(func, iterations=5):
    """Run function multiple times and get stats"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        result = func()
        duration = time.time() - start
        times.append(duration)
    
    return {
        "min": min(times),
        "max": max(times),
        "avg": statistics.mean(times),
        "median": statistics.median(times),
        "iterations": iterations
    }


def test_embedding_performance():
    """Test embedding generation performance"""
    log("\n" + "="*60, "INFO")
    log("Testing Embedding Performance", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        
        # Single embedding benchmark
        log("\nBenchmark: Single embedding", "INFO")
        
        def single_embed():
            return embedding_pipeline.generate_embedding("Sugar 1kg चीनी")
        
        stats = benchmark(single_embed, iterations=10)
        
        log(f"Min: {stats['min']*1000:.2f}ms", "INFO")
        log(f"Max: {stats['max']*1000:.2f}ms", "INFO")
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        log(f"Median: {stats['median']*1000:.2f}ms", "INFO")
        
        if stats['avg'] < 1.0:  # Under 1 second
            log(f"✓ Performance acceptable", "SUCCESS")
        else:
            log(f"⚠ Performance slow (avg {stats['avg']*1000:.2f}ms)", "WARNING")
        
        # Batch embedding benchmark
        log("\nBenchmark: Batch embedding (5 items)", "INFO")
        
        texts = [
            "Sugar 1kg",
            "Rice 5kg basmati",
            "Salt 500g",
            "Cooking Oil 2L",
            "Milk 1L"
        ]
        
        def batch_embed():
            return embedding_pipeline.generate_embeddings_batch(texts)
        
        stats = benchmark(batch_embed, iterations=5)
        
        log(f"Min: {stats['min']*1000:.2f}ms", "INFO")
        log(f"Max: {stats['max']*1000:.2f}ms", "INFO")
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        log(f"Per item: {(stats['avg']/len(texts))*1000:.2f}ms", "INFO")
        
        return True
        
    except Exception as e:
        log(f"✗ Embedding performance test failed: {e}", "ERROR")
        return False


def test_llm_performance():
    """Test LLM response performance"""
    log("\n" + "="*60, "INFO")
    log("Testing LLM Performance", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.llm_pipeline import llm_pipeline
        
        prompt = """You are a billing assistant. User says: "I need sugar"
Return JSON: {"type": "BILL", "items": [{"name": "Sugar", "quantity": 1, "unit": "kg"}], "msg": "Added sugar", "should_stop": false}"""
        
        log("Benchmarking LLM response (3 iterations)...", "INFO")
        
        def llm_invoke():
            response, duration, model = llm_pipeline.invoke(prompt)
            return response
        
        stats = benchmark(llm_invoke, iterations=3)
        
        log(f"Min: {stats['min']*1000:.2f}ms", "INFO")
        log(f"Max: {stats['max']*1000:.2f}ms", "INFO")
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        log(f"Median: {stats['median']*1000:.2f}ms", "INFO")
        
        if stats['avg'] < 5.0:  # Under 5 seconds
            log(f"✓ Performance acceptable", "SUCCESS")
        else:
            log(f"⚠ Performance slow (avg {stats['avg']:.2f}s)", "WARNING")
        
        return True
        
    except Exception as e:
        log(f"✗ LLM performance test failed: {e}", "ERROR")
        return False


def test_database_query_performance():
    """Test database query performance"""
    log("\n" + "="*60, "INFO")
    log("Testing Database Query Performance", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import get_session
        from db.models import User, Item
        from sqlmodel import select
        
        session = next(get_session())
        
        # Benchmark user query
        log("\nBenchmark: User query", "INFO")
        
        def user_query():
            user = session.exec(select(User)).first()
            return user
        
        stats = benchmark(user_query, iterations=10)
        
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        
        if stats['avg'] < 0.1:  # Under 100ms
            log(f"✓ User query fast", "SUCCESS")
        else:
            log(f"⚠ User query slow", "WARNING")
        
        # Benchmark item query
        log("\nBenchmark: Item query (all items)", "INFO")
        
        user = session.exec(select(User)).first()
        if not user:
            log("⚠ No user found, skipping", "WARNING")
            return True
        
        def item_query():
            items = session.exec(
                select(Item).where(Item.owner_id == user.id)
            ).all()
            return items
        
        stats = benchmark(item_query, iterations=10)
        
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        
        if stats['avg'] < 0.5:  # Under 500ms
            log(f"✓ Item query fast", "SUCCESS")
        else:
            log(f"⚠ Item query slow", "WARNING")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ Database performance test failed: {e}", "ERROR")
        return False


def test_vector_search_performance():
    """Test vector similarity search performance"""
    log("\n" + "="*60, "INFO")
    log("Testing Vector Search Performance", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        from sqlmodel import text
        
        # Create test vector
        test_vector = [0.1] * 768
        vector_str = "[" + ",".join(str(v) for v in test_vector) + "]"
        
        log("Benchmarking vector similarity search...", "INFO")
        
        def vector_search():
            with engine.connect() as conn:
                query = text(f"""
                    SELECT 1 as id, '{vector_str}'::vector <=> '{vector_str}'::vector as distance
                """)
                result = conn.execute(query).fetchone()
                return result
        
        stats = benchmark(vector_search, iterations=10)
        
        log(f"Min: {stats['min']*1000:.2f}ms", "INFO")
        log(f"Max: {stats['max']*1000:.2f}ms", "INFO")
        log(f"Avg: {stats['avg']*1000:.2f}ms", "INFO")
        
        if stats['avg'] < 0.1:  # Under 100ms
            log(f"✓ Vector search fast", "SUCCESS")
        else:
            log(f"⚠ Vector search slow", "WARNING")
        
        return True
        
    except Exception as e:
        log(f"✗ Vector search performance test failed: {e}", "ERROR")
        return False


def test_end_to_end_performance():
    """Test complete RAG query end-to-end"""
    log("\n" + "="*60, "INFO")
    log("Testing End-to-End RAG Performance", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        from pipeline.retrieval_pipeline import RetrievalPipeline
        from pipeline.prompt_pipeline import PromptPipeline
        from pipeline.llm_pipeline import llm_pipeline
        from db.database import engine, get_session
        from db.models import User
        from sqlmodel import select
        
        # Get test user
        session = next(get_session())
        user = session.exec(select(User)).first()
        
        if not user:
            log("⚠ No user found, skipping", "WARNING")
            return True
        
        user_id = user.id
        session.close()
        
        query = "I need sugar and rice"
        
        log(f"Benchmarking full RAG query (2 iterations)...", "INFO")
        
        def full_rag():
            # Embedding
            query_embedding = embedding_pipeline.generate_embedding(query)
            
            # Retrieval
            retrieval = RetrievalPipeline(engine)
            items = retrieval.retrieve_items(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=5
            )
            
            # Prompt
            prompt_builder = PromptPipeline()
            prompt = prompt_builder.build_simple_prompt(
                user_query=query,
                items=items,
                shop_category="Kirana"
            )
            
            # LLM
            response, duration, model = llm_pipeline.invoke(prompt)
            
            return response
        
        stats = benchmark(full_rag, iterations=2)
        
        log(f"Min: {stats['min']*1000:.2f}ms", "INFO")
        log(f"Max: {stats['max']*1000:.2f}ms", "INFO")
        log(f"Avg: {stats['avg']*1000:.2f}ms ({stats['avg']:.2f}s)", "INFO")
        
        if stats['avg'] < 5.0:  # Under 5 seconds
            log(f"✓ End-to-end performance acceptable", "SUCCESS")
        else:
            log(f"⚠ End-to-end slow (avg {stats['avg']:.2f}s)", "WARNING")
        
        return True
        
    except Exception as e:
        log(f"✗ End-to-end performance test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}PERFORMANCE BENCHMARK SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "embedding": test_embedding_performance(),
        "llm": test_llm_performance(),
        "database": test_database_query_performance(),
        "vector_search": test_vector_search_performance(),
        "end_to_end": test_end_to_end_performance()
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
