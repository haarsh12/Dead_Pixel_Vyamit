"""
Embedding Models Test - Gemini Embeddings
Tests embedding generation and quality
"""
import os
import time
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message, level="INFO"):
    """Colored logging"""
    color = {
        "INFO": BLUE,
        "SUCCESS": GREEN,
        "ERROR": RED,
        "WARNING": YELLOW
    }.get(level, RESET)
    print(f"{color}[{level}]{RESET} {message}")


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def test_gemini_embedding_api():
    """Test Gemini Embedding API directly"""
    log("\n" + "="*60, "INFO")
    log("Testing Gemini Embedding API", "INFO")
    log("="*60, "INFO")
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        log("GEMINI_API_KEY not found in .env", "ERROR")
        return False
    
    log(f"API Key: {api_key[:10]}...{api_key[-5:]}", "INFO")
    
    try:
        import google.generativeai as genai
        log("✓ google-generativeai package installed", "SUCCESS")
        
        # Configure
        genai.configure(api_key=api_key)
        log("✓ API configured", "SUCCESS")
        
        # Test single embedding
        log("\nTest 1: Single text embedding", "INFO")
        test_text = "Sugar 1kg चीनी"
        
        start = time.time()
        result = genai.embed_content(
            model="models/embedding-001",
            content=test_text,
            task_type="retrieval_document"
        )
        duration = time.time() - start
        
        embedding = result['embedding']
        log(f"✓ Generated embedding in {duration*1000:.2f}ms", "SUCCESS")
        log(f"Dimension: {len(embedding)}", "INFO")
        log(f"Sample values: {embedding[:5]}", "INFO")
        
        if len(embedding) != 768:
            log(f"✗ Wrong dimension: {len(embedding)}, expected 768", "ERROR")
            return False
        
        # Test batch embedding
        log("\nTest 2: Batch embeddings", "INFO")
        test_texts = [
            "Sugar 1kg",
            "Rice 5kg",
            "Salt 500g",
            "Oil 2L",
            "Milk 1L"
        ]
        
        start = time.time()
        result = genai.embed_content(
            model="models/embedding-001",
            content=test_texts,
            task_type="retrieval_document"
        )
        duration = time.time() - start
        
        embeddings = result['embedding']
        log(f"✓ Generated {len(embeddings)} embeddings in {duration*1000:.2f}ms", "SUCCESS")
        log(f"Avg time per embedding: {(duration/len(embeddings))*1000:.2f}ms", "INFO")
        
        # Test semantic similarity
        log("\nTest 3: Semantic similarity", "INFO")
        
        query = "I need chini"
        similar_texts = ["Sugar", "Rice", "Salt"]
        
        # Generate query embedding
        query_result = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="retrieval_query"
        )
        query_emb = query_result['embedding']
        
        # Generate document embeddings
        doc_result = genai.embed_content(
            model="models/embedding-001",
            content=similar_texts,
            task_type="retrieval_document"
        )
        doc_embs = doc_result['embedding']
        
        # Calculate similarities
        similarities = []
        for text, emb in zip(similar_texts, doc_embs):
            sim = cosine_similarity(query_emb, emb)
            similarities.append((text, sim))
            log(f"  '{query}' vs '{text}': {sim:.4f}", "INFO")
        
        # Check if most similar is Sugar
        similarities.sort(key=lambda x: x[1], reverse=True)
        most_similar = similarities[0][0]
        
        if most_similar == "Sugar":
            log(f"✓ Correct semantic match: '{most_similar}'", "SUCCESS")
        else:
            log(f"⚠ Unexpected match: '{most_similar}' (expected 'Sugar')", "WARNING")
        
        return True
        
    except ImportError:
        log("✗ google-generativeai not installed", "ERROR")
        log("Install: pip install google-generativeai", "WARNING")
        return False
    except Exception as e:
        log(f"✗ Gemini Embedding test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_pipeline():
    """Test the embedding pipeline"""
    log("\n" + "="*60, "INFO")
    log("Testing Embedding Pipeline", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        
        # Test single embedding
        log("\nTest 1: Single embedding", "INFO")
        text = "Sugar चीनी 1kg"
        
        start = time.time()
        embedding = embedding_pipeline.generate_embedding(text)
        duration = time.time() - start
        
        log(f"✓ Generated in {duration*1000:.2f}ms", "SUCCESS")
        log(f"Dimension: {len(embedding)}", "INFO")
        log(f"Sample: {embedding[:3]}", "INFO")
        
        if len(embedding) != 768:
            log(f"✗ Wrong dimension: {len(embedding)}", "ERROR")
            return False
        
        # Test batch embeddings
        log("\nTest 2: Batch embeddings", "INFO")
        texts = [
            "Sugar 1kg",
            "Rice 5kg basmati",
            "Salt 500g",
            "Cooking Oil 2L",
            "Milk 1L dairy"
        ]
        
        start = time.time()
        embeddings = embedding_pipeline.generate_embeddings_batch(texts)
        duration = time.time() - start
        
        log(f"✓ Generated {len(embeddings)} embeddings in {duration*1000:.2f}ms", "SUCCESS")
        log(f"Avg: {(duration/len(embeddings))*1000:.2f}ms per embedding", "INFO")
        
        # Test query embedding with timing
        log("\nTest 3: Query embedding with timing", "INFO")
        query = "I need चीनी and नमक"
        
        embedding, query_duration = embedding_pipeline.generate_query_embedding(query)
        
        log(f"✓ Query embedded in {query_duration*1000:.2f}ms", "SUCCESS")
        log(f"Dimension: {len(embedding)}", "INFO")
        
        # Test pipeline info
        log("\nTest 4: Pipeline info", "INFO")
        info = embedding_pipeline.get_info()
        log(f"Provider: {info['provider']}", "INFO")
        log(f"Model: {info['model']}", "INFO")
        log(f"Dimension: {info['dimension']}", "INFO")
        log(f"Initialized: {info['initialized']}", "INFO")
        
        return True
        
    except Exception as e:
        log(f"✗ Embedding Pipeline test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_quality():
    """Test embedding quality with semantic tests"""
    log("\n" + "="*60, "INFO")
    log("Testing Embedding Quality (Semantic Tests)", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        
        # Test cases: (query, expected_match, distractors)
        test_cases = [
            {
                "query": "chini चीनी sugar",
                "items": ["Sugar 1kg", "Salt 500g", "Rice 5kg"],
                "expected": "Sugar 1kg"
            },
            {
                "query": "namak salt नमक",
                "items": ["Sugar", "Salt", "Pepper"],
                "expected": "Salt"
            },
            {
                "query": "दूध milk dairy",
                "items": ["Milk 1L", "Water 1L", "Juice 500ml"],
                "expected": "Milk 1L"
            },
            {
                "query": "तेल oil cooking",
                "items": ["Cooking Oil", "Ghee", "Butter"],
                "expected": "Cooking Oil"
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for idx, test in enumerate(test_cases, 1):
            log(f"\nTest Case {idx}: '{test['query']}'", "INFO")
            
            # Generate embeddings
            query_emb = embedding_pipeline.generate_embedding(test['query'])
            item_embs = embedding_pipeline.generate_embeddings_batch(test['items'])
            
            # Calculate similarities
            similarities = []
            for item, emb in zip(test['items'], item_embs):
                sim = cosine_similarity(query_emb, emb)
                similarities.append((item, sim))
                log(f"  {item}: {sim:.4f}", "INFO")
            
            # Find best match
            similarities.sort(key=lambda x: x[1], reverse=True)
            best_match = similarities[0][0]
            
            if best_match == test['expected']:
                log(f"✓ Correct: '{best_match}'", "SUCCESS")
                passed += 1
            else:
                log(f"✗ Wrong: got '{best_match}', expected '{test['expected']}'", "ERROR")
        
        log(f"\n{'='*60}", "INFO")
        log(f"Semantic Quality: {passed}/{total} tests passed", "INFO")
        log(f"{'='*60}", "INFO")
        
        return passed == total
        
    except Exception as e:
        log(f"✗ Quality test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all embedding tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}EMBEDDING MODELS TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "gemini_api": test_gemini_embedding_api(),
        "pipeline": test_embedding_pipeline(),
        "quality": test_embedding_quality()
    }
    
    # Summary
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
