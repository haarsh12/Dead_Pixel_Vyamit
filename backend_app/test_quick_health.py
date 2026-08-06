"""
Quick Health Check
Fast check to verify all systems are operational
"""
import os
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


def check_env_vars():
    """Check critical environment variables"""
    log("\n" + "="*60, "INFO")
    log("Checking Environment Variables", "INFO")
    log("="*60, "INFO")
    
    required = {
        "GEMINI_API_KEY": "Gemini API",
        "DATABASE_URL": "Database",
        "SECRET_KEY": "JWT Security"
    }
    
    optional = {
        "MISTRAL_API_KEY": "Mistral LLM",
        "TWILIO_ACCOUNT_SID": "SMS Service",
        "TWILIO_AUTH_TOKEN": "SMS Service"
    }
    
    all_ok = True
    
    for key, name in required.items():
        value = os.getenv(key)
        if value:
            log(f"✓ {name}: Set", "SUCCESS")
        else:
            log(f"✗ {name}: Missing", "ERROR")
            all_ok = False
    
    for key, name in optional.items():
        value = os.getenv(key)
        if value:
            log(f"✓ {name}: Set", "SUCCESS")
        else:
            log(f"⚠ {name}: Not set (optional)", "WARNING")
    
    return all_ok


def check_gemini_api():
    """Quick Gemini API check"""
    log("\n" + "="*60, "INFO")
    log("Checking Gemini API", "INFO")
    log("="*60, "INFO")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            log("✗ API key not found", "ERROR")
            return False
        
        genai.configure(api_key=api_key)
        
        # Test embedding
        result = genai.embed_content(
            model="models/embedding-001",
            content="test",
            task_type="retrieval_query"
        )
        
        if result and 'embedding' in result:
            log(f"✓ Gemini Embedding API working ({len(result['embedding'])}D)", "SUCCESS")
        
        # Test LLM
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content("Say 'OK'")
        
        if response and response.text:
            log(f"✓ Gemini LLM API working", "SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"✗ Gemini API failed: {str(e)[:100]}", "ERROR")
        return False


def check_mistral_api():
    """Quick Mistral API check"""
    log("\n" + "="*60, "INFO")
    log("Checking Mistral API", "INFO")
    log("="*60, "INFO")
    
    try:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            log("⚠ API key not set (optional)", "WARNING")
            return True
        
        from mistralai import Mistral
        
        client = Mistral(api_key=api_key)
        
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10
        )
        
        if response and response.choices:
            log(f"✓ Mistral API working", "SUCCESS")
            return True
        
        return False
        
    except Exception as e:
        log(f"✗ Mistral API failed: {str(e)[:100]}", "ERROR")
        return False


def check_database():
    """Quick database check"""
    log("\n" + "="*60, "INFO")
    log("Checking Database", "INFO")
    log("="*60, "INFO")
    
    try:
        from db.database import engine
        
        with engine.connect() as conn:
            result = conn.execute("SELECT 1").fetchone()
            log("✓ Database connection OK", "SUCCESS")
        
        # Check pgvector
        with engine.connect() as conn:
            result = conn.execute(
                "SELECT extname FROM pg_extension WHERE extname='vector'"
            ).fetchone()
            
            if result:
                log("✓ pgvector extension installed", "SUCCESS")
            else:
                log("✗ pgvector extension missing", "ERROR")
                return False
        
        return True
        
    except Exception as e:
        log(f"✗ Database check failed: {str(e)[:100]}", "ERROR")
        return False


def check_pipelines():
    """Quick pipeline check"""
    log("\n" + "="*60, "INFO")
    log("Checking Pipelines", "INFO")
    log("="*60, "INFO")
    
    try:
        # Embedding pipeline
        from pipeline.embedding_pipeline import embedding_pipeline
        
        embedding = embedding_pipeline.generate_embedding("test")
        if len(embedding) == 768:
            log("✓ Embedding pipeline working", "SUCCESS")
        else:
            log(f"✗ Embedding pipeline wrong dimension: {len(embedding)}", "ERROR")
            return False
        
        # LLM pipeline
        from pipeline.llm_pipeline import llm_pipeline
        
        response, duration, model = llm_pipeline.invoke("Say OK")
        if response:
            log(f"✓ LLM pipeline working (model: {model})", "SUCCESS")
        else:
            log("✗ LLM pipeline failed", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        log(f"✗ Pipeline check failed: {str(e)[:100]}", "ERROR")
        return False


def check_server():
    """Check if server is running"""
    log("\n" + "="*60, "INFO")
    log("Checking Server", "INFO")
    log("="*60, "INFO")
    
    try:
        import requests
        
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            log(f"✓ Server is running at {base_url}", "SUCCESS")
            
            # Check info endpoint
            response = requests.get(f"{base_url}/info")
            if response.status_code == 200:
                data = response.json()
                log(f"✓ Server version: {data.get('version')}", "SUCCESS")
                log(f"✓ Embedding: {data.get('embedding_provider')}", "SUCCESS")
            
            return True
        else:
            log(f"⚠ Server returned status {response.status_code}", "WARNING")
            return False
        
    except Exception as e:
        log(f"⚠ Server not reachable: {str(e)[:100]}", "WARNING")
        log("Start server with: python main.py", "INFO")
        return False


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}QUICK HEALTH CHECK{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "Environment": check_env_vars(),
        "Gemini API": check_gemini_api(),
        "Mistral API": check_mistral_api(),
        "Database": check_database(),
        "Pipelines": check_pipelines(),
        "Server": check_server()
    }
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}HEALTH CHECK SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    for name, status in results.items():
        if status:
            print(f"{GREEN}✓{RESET} {name:20} HEALTHY")
        else:
            print(f"{RED}✗{RESET} {name:20} UNHEALTHY")
    
    healthy = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n{BLUE}Status: {healthy}/{total} systems healthy{RESET}")
    
    if healthy == total:
        print(f"{GREEN}All systems operational!{RESET}")
    elif healthy >= total - 1:
        print(f"{YELLOW}Minor issues detected{RESET}")
    else:
        print(f"{RED}Critical issues detected{RESET}")
    
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return healthy >= total - 1


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
