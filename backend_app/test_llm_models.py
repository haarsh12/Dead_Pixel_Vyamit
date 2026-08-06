"""
LLM Models Test - Gemini and Mistral
Direct API testing for both LLM providers
"""
import os
import time
import json
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


def test_gemini_api():
    """Test Gemini API directly"""
    log("\n" + "="*60, "INFO")
    log("Testing Gemini API", "INFO")
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
        
        # Test models
        models_to_test = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
        
        successful_models = []
        
        for model_name in models_to_test:
            log(f"\nTesting model: {model_name}", "INFO")
            
            try:
                model = genai.GenerativeModel(model_name)
                
                start = time.time()
                response = model.generate_content(
                    "Return JSON: {\"type\": \"QUERY\", \"items\": [], \"msg\": \"Hello\", \"should_stop\": false}",
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 200
                    }
                )
                duration = time.time() - start
                
                content = response.text
                log(f"Response ({duration*1000:.2f}ms): {content[:100]}...", "INFO")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    log(f"✓ {model_name} - Valid JSON response", "SUCCESS")
                    successful_models.append(model_name)
                except json.JSONDecodeError:
                    log(f"✗ {model_name} - Invalid JSON", "ERROR")
                
            except Exception as e:
                log(f"✗ {model_name} failed: {e}", "ERROR")
        
        log(f"\n{'='*60}", "INFO")
        log(f"Gemini Models Working: {len(successful_models)}/{len(models_to_test)}", "INFO")
        for model in successful_models:
            log(f"  ✓ {model}", "SUCCESS")
        log(f"{'='*60}", "INFO")
        
        return len(successful_models) > 0
        
    except ImportError:
        log("✗ google-generativeai not installed", "ERROR")
        log("Install: pip install google-generativeai", "WARNING")
        return False
    except Exception as e:
        log(f"✗ Gemini test failed: {e}", "ERROR")
        return False


def test_mistral_api():
    """Test Mistral API directly"""
    log("\n" + "="*60, "INFO")
    log("Testing Mistral API", "INFO")
    log("="*60, "INFO")
    
    api_key = os.getenv("MISTRAL_API_KEY")
    
    if not api_key:
        log("MISTRAL_API_KEY not found in .env", "ERROR")
        log("Note: Mistral is optional, will fallback to Gemini", "WARNING")
        return False
    
    log(f"API Key: {api_key[:10]}...{api_key[-5:]}", "INFO")
    
    try:
        from mistralai import Mistral
        log("✓ mistralai package installed", "SUCCESS")
        
        # Initialize client
        client = Mistral(api_key=api_key)
        log("✓ Client initialized", "SUCCESS")
        
        # Test models
        models_to_test = [
            "mistral-large-latest",
            "mistral-small-latest"
        ]
        
        successful_models = []
        
        for model_name in models_to_test:
            log(f"\nTesting model: {model_name}", "INFO")
            
            try:
                start = time.time()
                response = client.chat.complete(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": "Return JSON: {\"type\": \"QUERY\", \"items\": [], \"msg\": \"Hello\", \"should_stop\": false}"
                        }
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                duration = time.time() - start
                
                content = response.choices[0].message.content
                log(f"Response ({duration*1000:.2f}ms): {content[:100]}...", "INFO")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    log(f"✓ {model_name} - Valid JSON response", "SUCCESS")
                    successful_models.append(model_name)
                except json.JSONDecodeError:
                    log(f"✗ {model_name} - Invalid JSON", "ERROR")
                
            except Exception as e:
                log(f"✗ {model_name} failed: {e}", "ERROR")
        
        log(f"\n{'='*60}", "INFO")
        log(f"Mistral Models Working: {len(successful_models)}/{len(models_to_test)}", "INFO")
        for model in successful_models:
            log(f"  ✓ {model}", "SUCCESS")
        log(f"{'='*60}", "INFO")
        
        return len(successful_models) > 0
        
    except ImportError:
        log("✗ mistralai not installed", "ERROR")
        log("Install: pip install mistralai", "WARNING")
        return False
    except Exception as e:
        log(f"✗ Mistral test failed: {e}", "ERROR")
        return False


def test_llm_pipeline():
    """Test the LLM pipeline with fallback"""
    log("\n" + "="*60, "INFO")
    log("Testing LLM Pipeline (with fallback)", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.llm_pipeline import llm_pipeline
        
        test_prompt = """
You are a billing assistant. Return JSON only.

User: I need sugar
Response format: {"type": "BILL", "items": [{"name": "Sugar", "quantity": 1, "unit": "kg"}], "msg": "Added sugar", "should_stop": false}
"""
        
        log("Invoking LLM pipeline...", "INFO")
        start = time.time()
        response, duration, model_used = llm_pipeline.invoke(test_prompt)
        total_time = time.time() - start
        
        log(f"Model used: {model_used}", "INFO")
        log(f"Duration: {duration*1000:.2f}ms (total: {total_time*1000:.2f}ms)", "INFO")
        log(f"Response: {json.dumps(response, indent=2)}", "INFO")
        
        # Validate response
        is_valid = llm_pipeline.validate_response(response)
        
        if is_valid:
            log("✓ LLM Pipeline working with valid response", "SUCCESS")
            return True
        else:
            log("✗ Invalid response structure", "ERROR")
            return False
        
    except Exception as e:
        log(f"✗ LLM Pipeline test failed: {e}", "ERROR")
        return False


def main():
    """Run all LLM tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}LLM MODELS TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "gemini": test_gemini_api(),
        "mistral": test_mistral_api(),
        "pipeline": test_llm_pipeline()
    }
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    for name, success in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
        print(f"{name.upper():15} {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
