"""
RAG Pipeline Integration Test
Tests the complete RAG pipeline flow
"""
import os
import time
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


def test_prompt_pipeline():
    """Test prompt building"""
    log("\n" + "="*60, "INFO")
    log("Testing Prompt Pipeline", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.prompt_pipeline import PromptPipeline
        
        prompt_builder = PromptPipeline()
        
        # Test simple prompt
        log("Building simple prompt...", "INFO")
        items = [
            {"names": ["Sugar", "चीनी"], "price": 50, "unit": "kg"},
            {"names": ["Rice", "चावल"], "price": 60, "unit": "kg"}
        ]
        
        prompt = prompt_builder.build_simple_prompt(
            user_query="I need sugar",
            items=items,
            shop_category="Kirana"
        )
        
        log(f"✓ Simple prompt built: {len(prompt)} chars", "SUCCESS")
        log(f"Preview: {prompt[:100]}...", "INFO")
        
        # Test RAG prompt
        log("\nBuilding RAG prompt...", "INFO")
        analytics = {
            "total_revenue": 50000,
            "total_bills": 150,
            "avg_bill": 333
        }
        
        prompt = prompt_builder.build_rag_prompt(
            user_query="What are my top selling items?",
            items=items,
            analytics=analytics,
            customers=[],
            shop_category="Kirana"
        )
        
        log(f"✓ RAG prompt built: {len(prompt)} chars", "SUCCESS")
        log(f"Contains items: {'Sugar' in prompt}", "INFO")
        log(f"Contains analytics: {'revenue' in prompt.lower()}", "INFO")
        
        return True
        
    except Exception as e:
        log(f"✗ Prompt pipeline test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_retrieval_pipeline():
    """Test retrieval pipeline"""
    log("\n" + "="*60, "INFO")
    log("Testing Retrieval Pipeline", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.retrieval_pipeline import RetrievalPipeline
        from pipeline.embedding_pipeline import embedding_pipeline
        from db.database import engine
        
        retrieval = RetrievalPipeline(engine)
        
        # Generate test query embedding
        log("Generating query embedding...", "INFO")
        query = "sugar चीनी"
        query_embedding = embedding_pipeline.generate_embedding(query)
        
        log(f"✓ Query embedding: {len(query_embedding)}D", "SUCCESS")
        
        # Test item retrieval
        log("\nRetrieving items...", "INFO")
        
        # Get first user ID from database
        from db.database import get_session
        from db.models import User
        from sqlmodel import select
        
        session = next(get_session())
        user = session.exec(select(User)).first()
        
        if not user:
            log("⚠ No user found, skipping retrieval", "WARNING")
            return True
        
        items = retrieval.retrieve_items(
            query_embedding=query_embedding,
            user_id=user.id,
            top_k=5
        )
        
        log(f"✓ Retrieved {len(items)} items", "SUCCESS")
        
        for item in items:
            log(f"  - {item.get('name', 'Unknown')}: ₹{item.get('price', 0)}", "INFO")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ Retrieval pipeline test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_full_rag_flow():
    """Test complete RAG flow"""
    log("\n" + "="*60, "INFO")
    log("Testing Full RAG Flow", "INFO")
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
        
        # Step 1: Generate query embedding
        log("\nStep 1: Generating embedding...", "INFO")
        query = "I need 2kg sugar"
        start = time.time()
        query_embedding = embedding_pipeline.generate_embedding(query)
        embed_time = time.time() - start
        log(f"✓ Embedding generated in {embed_time*1000:.2f}ms", "SUCCESS")
        
        # Step 2: Retrieve context
        log("\nStep 2: Retrieving context...", "INFO")
        start = time.time()
        retrieval = RetrievalPipeline(engine)
        items = retrieval.retrieve_items(
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=5
        )
        retrieve_time = time.time() - start
        log(f"✓ Retrieved {len(items)} items in {retrieve_time*1000:.2f}ms", "SUCCESS")
        
        # Step 3: Build prompt
        log("\nStep 3: Building prompt...", "INFO")
        start = time.time()
        prompt_builder = PromptPipeline()
        prompt = prompt_builder.build_simple_prompt(
            user_query=query,
            items=items,
            shop_category="Kirana"
        )
        prompt_time = time.time() - start
        log(f"✓ Prompt built in {prompt_time*1000:.2f}ms", "SUCCESS")
        
        # Step 4: Get LLM response
        log("\nStep 4: Getting LLM response...", "INFO")
        start = time.time()
        response, llm_time, model_used = llm_pipeline.invoke(prompt)
        total_llm_time = time.time() - start
        
        log(f"✓ LLM responded in {total_llm_time*1000:.2f}ms", "SUCCESS")
        log(f"Model used: {model_used}", "INFO")
        log(f"Response type: {response.get('type')}", "INFO")
        log(f"Message: {response.get('msg', '')[:100]}", "INFO")
        
        # Validate response
        is_valid = llm_pipeline.validate_response(response)
        
        if is_valid:
            log("✓ Response structure valid", "SUCCESS")
        else:
            log("✗ Invalid response structure", "ERROR")
            return False
        
        # Total time
        total_time = embed_time + retrieve_time + prompt_time + total_llm_time
        log(f"\nTotal RAG pipeline time: {total_time*1000:.2f}ms", "INFO")
        
        return True
        
    except Exception as e:
        log(f"✗ Full RAG flow test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_rag_error_handling():
    """Test RAG error handling"""
    log("\n" + "="*60, "INFO")
    log("Testing RAG Error Handling", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.llm_pipeline import llm_pipeline
        
        # Test with empty prompt
        log("Testing empty prompt...", "INFO")
        response, duration, model = llm_pipeline.invoke("")
        
        if response.get("type") == "ERROR":
            log("✓ Empty prompt handled correctly", "SUCCESS")
        else:
            log("⚠ Empty prompt returned unexpected response", "WARNING")
        
        # Test response validation
        log("\nTesting response validation...", "INFO")
        
        valid_response = {
            "type": "BILL",
            "items": [],
            "msg": "Test",
            "should_stop": False
        }
        
        is_valid = llm_pipeline.validate_response(valid_response)
        if is_valid:
            log("✓ Valid response accepted", "SUCCESS")
        else:
            log("✗ Valid response rejected", "ERROR")
            return False
        
        invalid_response = {
            "type": "INVALID",
            "items": []
        }
        
        is_valid = llm_pipeline.validate_response(invalid_response)
        if not is_valid:
            log("✓ Invalid response rejected", "SUCCESS")
        else:
            log("✗ Invalid response accepted", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        log(f"✗ Error handling test failed: {e}", "ERROR")
        return False


def test_multilanguage_queries():
    """Test multi-language query handling"""
    log("\n" + "="*60, "INFO")
    log("Testing Multi-language Queries", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        
        test_queries = [
            "I need sugar",
            "मुझे चीनी चाहिए",
            "sugar चीनी",
            "2 kg चावल",
            "salt and नमक"
        ]
        
        log("Testing embeddings for multiple languages...", "INFO")
        
        for query in test_queries:
            embedding = embedding_pipeline.generate_embedding(query)
            
            if len(embedding) == 768:
                log(f"✓ '{query}': {len(embedding)}D", "SUCCESS")
            else:
                log(f"✗ '{query}': Wrong dimension {len(embedding)}", "ERROR")
                return False
        
        return True
        
    except Exception as e:
        log(f"✗ Multi-language test failed: {e}", "ERROR")
        return False


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}RAG PIPELINE TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "prompt_pipeline": test_prompt_pipeline(),
        "retrieval_pipeline": test_retrieval_pipeline(),
        "full_rag_flow": test_full_rag_flow(),
        "error_handling": test_rag_error_handling(),
        "multilanguage": test_multilanguage_queries()
    }
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    for name, success in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
        print(f"{name.upper():25} {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
