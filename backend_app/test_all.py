"""Safe master runner for local, integration, and benchmark checks."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=False)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def log(message: str, level: str = "INFO") -> None:
    color = {
        "INFO": BLUE,
        "SUCCESS": GREEN,
        "ERROR": RED,
        "WARNING": YELLOW,
        "HEADER": CYAN,
    }[level]
    print(f"{color}{message}{RESET}")


def enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def run_test_file(filename: str) -> bool:
    """Run one suite with a bounded timeout and the backend as its working directory."""
    timeout = int(os.getenv("TEST_TIMEOUT_SECONDS", "120"))
    log(f"\n{'=' * 70}", "HEADER")
    log(f"Running: {filename}", "HEADER")
    log(f"{'=' * 70}", "HEADER")
    try:
        result = subprocess.run(
            [sys.executable, filename],
            cwd=BACKEND_DIR,
            # Child suites include Hindi text and status glyphs. Force UTF-8 so
            # they work even when launched from a legacy Windows code page.
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log(f"{filename} exceeded the {timeout}s timeout.", "ERROR")
        return False
    except OSError as exc:
        log(f"Could not run {filename}: {exc}", "ERROR")
        return False

    if result.returncode == 0:
        log(f"{filename} completed successfully", "SUCCESS")
        return True
    log(f"{filename} failed with exit code {result.returncode}", "ERROR")
    return False


def check_server_running() -> bool:
    try:
        import requests

        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        return requests.get(f"{base_url}/health", timeout=5).status_code == 200
    except Exception:
        return False


def check_environment() -> bool:
    """Check only dependencies required for the default local test run."""
    log("\nChecking environment variables...")
    required = {"DATABASE_URL": "database integration tests"}
    optional = {
        "GEMINI_API_KEY": "live Gemini checks",
        "MISTRAL_API_KEY": "live Mistral checks",
    }
    missing = []
    for key, purpose in required.items():
        if os.getenv(key, "").strip():
            log(f"{key}: configured", "SUCCESS")
        else:
            log(f"{key}: missing ({purpose})", "ERROR")
            missing.append(key)
    for key, purpose in optional.items():
        state = "configured" if os.getenv(key, "").strip() else "not configured"
        log(f"{key}: {state} ({purpose})", "INFO")
    return not missing


def main() -> int:
    started = datetime.now()
    log("\n" + "=" * 70, "HEADER")
    log("MASTER TEST SUITE", "HEADER")
    log(f"Started: {started:%Y-%m-%d %H:%M:%S}", "HEADER")
    log("=" * 70, "HEADER")

    environment_ok = check_environment()
    if not environment_ok:
        log("Default database checks will fail until DATABASE_URL is configured.", "WARNING")

    suites = [
        ("Database", "test_database.py", "database and pgvector integration", None),
        ("Services", "test_services.py", "OTP, security, and configuration", None),
        ("RAG pipeline", "test_rag_pipeline.py", "local prompt/retrieval/error contracts", None),
        ("Embedding models", "test_embeddings.py", "billable Gemini integration", "RUN_LIVE_AI_TESTS"),
        ("LLM models", "test_llm_models.py", "billable provider integration", "RUN_LIVE_AI_TESTS"),
        ("Performance", "test_performance.py", "database and API benchmarks", "RUN_BENCHMARKS"),
        ("API endpoints", "test_api.py", "running-server endpoint checks", "SERVER"),
    ]

    results: dict[str, str] = {}
    for name, filename, description, gate in suites:
        log(f"\n{name}: {description}", "INFO")
        if gate == "SERVER":
            if not check_server_running():
                log("Skipped because the API server is not running.", "WARNING")
                results[name] = "skipped"
                continue
        elif gate and not enabled(gate):
            log(f"Skipped; set {gate}=1 to enable this suite.", "WARNING")
            results[name] = "skipped"
            continue
        results[name] = "passed" if run_test_file(filename) else "failed"

    log("\n" + "=" * 70, "HEADER")
    log("FINAL SUMMARY", "HEADER")
    log("=" * 70, "HEADER")
    for name, status in results.items():
        level = "SUCCESS" if status == "passed" else "ERROR" if status == "failed" else "WARNING"
        log(f"{name:20} {status.upper()}", level)

    failed = sum(status == "failed" for status in results.values())
    passed = sum(status == "passed" for status in results.values())
    skipped = sum(status == "skipped" for status in results.values())
    elapsed = (datetime.now() - started).total_seconds()
    log(f"\nPassed: {passed}  Failed: {failed}  Skipped: {skipped}")
    log(f"Duration: {elapsed:.2f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
