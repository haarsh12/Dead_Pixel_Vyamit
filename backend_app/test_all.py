"""
Master Test Runner
Runs all test suites in sequence
"""
import os
import sys
import subprocess
from datetime import datetime

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def log(message, level="INFO"):
    """Colored logging"""
    color = {
        "INFO": BLUE,
        "SUCCESS": GREEN,
        "ERROR": RED,
        "WARNING": YELLOW,
        "HEADER": CYAN
    }.get(level, RESET)
    print(f"{color}{message}{RESET}")


def run_test_file(filename):
    """Run a test file"""
    log(f"\n{'='*70}", "HEADER")
    log(f"Running: {filename}", "HEADER")
    log(f"{'='*70}", "HEADER")
    
    try:
        result = subprocess.run(
            [sys.executable, filename],
            cwd=os.path.dirname(__file__) or ".",
            capture_output=False,
            text=True
        )
        
        success = result.returncode == 0
        
        if success:
            log(f"✓ {filename} completed successfully", "SUCCESS")
        else:
            log(f"✗ {filename} failed with exit code {result.returncode}", "ERROR")
        
        return success
        
    except Exception as e:
        log(f"✗ Failed to run {filename}: {e}", "ERROR")
        return False


def check_server_running():
    """Check if backend server is running"""
    log("\nChecking if server is running...", "INFO")
    
    try:
        import requests
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            log("✓ Server is running", "SUCCESS")
            return True
        else:
            log(f"⚠ Server returned status {response.status_code}", "WARNING")
            return False
    except Exception as e:
        log(f"✗ Server not reachable: {e}", "ERROR")
        log("Please start the server: python main.py", "WARNING")
        return False


def check_environment():
    """Check environment variables"""
    log("\nChecking environment variables...", "INFO")
    
    required = {
        "GEMINI_API_KEY": "Required for embeddings and LLM fallback",
        "MISTRAL_API_KEY": "Optional for primary LLM",
        "DATABASE_URL": "Required for database connection"
    }
    
    issues = []
    
    for key, description in required.items():
        value = os.getenv(key)
        if value:
            log(f"✓ {key}: Set", "SUCCESS")
        else:
            log(f"✗ {key}: Missing - {description}", "ERROR")
            issues.append(key)
    
    return len(issues) == 0


def main():
    """Run all tests"""
    start_time = datetime.now()
    
    log("\n" + "="*70, "HEADER")
    log("MASTER TEST SUITE", "HEADER")
    log(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", "HEADER")
    log("="*70, "HEADER")
    
    # Check environment
    env_ok = check_environment()
    if not env_ok:
        log("\n⚠ Environment check failed. Some tests may fail.", "WARNING")
        log("Check your .env file", "WARNING")
    
    # Define test suites
    test_suites = [
        {
            "name": "Database",
            "file": "test_database.py",
            "description": "Tests database connection, models, and pgvector",
            "requires_server": False
        },
        {
            "name": "Services",
            "file": "test_services.py",
            "description": "Tests OTP, SMS, security, and config services",
            "requires_server": False
        },
        {
            "name": "Embedding Models",
            "file": "test_embeddings.py",
            "description": "Tests Gemini embeddings and semantic quality",
            "requires_server": False
        },
        {
            "name": "LLM Models",
            "file": "test_llm_models.py",
            "description": "Tests Gemini and Mistral LLM APIs",
            "requires_server": False
        },
        {
            "name": "RAG Pipeline",
            "file": "test_rag_pipeline.py",
            "description": "Tests RAG pipeline integration",
            "requires_server": False
        },
        {
            "name": "Performance",
            "file": "test_performance.py",
            "description": "Performance benchmarks for all components",
            "requires_server": False
        },
        {
            "name": "API Endpoints",
            "file": "test_api.py",
            "description": "Tests all REST API endpoints",
            "requires_server": True
        }
    ]
    
    results = {}
    
    for suite in test_suites:
        log(f"\n{'='*70}", "INFO")
        log(f"Test Suite: {suite['name']}", "INFO")
        log(f"Description: {suite['description']}", "INFO")
        log(f"{'='*70}", "INFO")
        
        # Check if server is required and running
        if suite['requires_server']:
            if not check_server_running():
                log(f"⊘ Skipping {suite['name']} - server not running", "WARNING")
                results[suite['name']] = "skipped"
                continue
        
        # Run test
        success = run_test_file(suite['file'])
        results[suite['name']] = "passed" if success else "failed"
    
    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    log("\n" + "="*70, "HEADER")
    log("FINAL SUMMARY", "HEADER")
    log("="*70, "HEADER")
    
    for name, status in results.items():
        if status == "passed":
            log(f"✓ {name:30} PASSED", "SUCCESS")
        elif status == "failed":
            log(f"✗ {name:30} FAILED", "ERROR")
        else:
            log(f"⊘ {name:30} SKIPPED", "WARNING")
    
    passed = sum(1 for s in results.values() if s == "passed")
    failed = sum(1 for s in results.values() if s == "failed")
    skipped = sum(1 for s in results.values() if s == "skipped")
    total = len(results)
    
    log(f"\nResults:", "INFO")
    log(f"  Passed:  {passed}/{total}", "SUCCESS" if passed == total else "INFO")
    log(f"  Failed:  {failed}/{total}", "ERROR" if failed > 0 else "INFO")
    log(f"  Skipped: {skipped}/{total}", "WARNING" if skipped > 0 else "INFO")
    
    log(f"\nDuration: {duration:.2f} seconds", "INFO")
    log(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
    log("="*70, "HEADER")
    
    # Exit code
    if failed > 0:
        log("\n⚠ Some tests failed!", "ERROR")
        return 1
    elif skipped > 0:
        log("\n⚠ Some tests were skipped", "WARNING")
        return 0
    else:
        log("\n✓ All tests passed!", "SUCCESS")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
