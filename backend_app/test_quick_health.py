"""Live operational health check for the backend and configured providers."""

import os

import requests
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message: str, level: str = "INFO") -> None:
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}[level]
    print(f"{color}[{level}]{RESET} {message}")


def check_environment() -> bool:
    required = ("DATABASE_URL", "SECRET_KEY")
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        log("Missing required configuration: " + ", ".join(missing), "ERROR")
        return False
    log("Required local configuration is present", "SUCCESS")
    return True


def check_database() -> bool:
    try:
        from db.database import engine

        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
            vector = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
        if vector is None:
            log("Database is reachable but pgvector is not installed", "ERROR")
            return False
        log("Database and pgvector are healthy", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Database health check failed: {exc}", "ERROR")
        return False


def check_gemini() -> bool:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        log("Gemini is not configured", "WARNING")
        return True
    try:
        from pipeline.embedding_pipeline import embedding_pipeline

        vector = embedding_pipeline.generate_embedding("health check")
        if len(vector) != 768:
            log(f"Gemini returned an unexpected embedding size: {len(vector)}", "ERROR")
            return False
        log("Gemini embeddings are healthy", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Gemini health check failed: {exc}", "ERROR")
        return False


def check_mistral() -> bool:
    if not os.getenv("MISTRAL_API_KEY", "").strip():
        log("Mistral is not configured", "WARNING")
        return True
    try:
        from pipeline.llm_pipeline import llm_pipeline

        response, _ = llm_pipeline.invoke_mistral(
            "Return JSON only: {\"type\":\"QUERY\",\"items\":[],\"msg\":\"OK\",\"should_stop\":false}"
        )
        if not llm_pipeline.validate_response(response):
            log("Mistral returned an invalid JSON response", "ERROR")
            return False
        log("Mistral is healthy", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Mistral health check failed: {exc}", "ERROR")
        return False


def check_server() -> bool:
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            log(f"API server returned HTTP {response.status_code}", "ERROR")
            return False
        log(f"API server is healthy at {base_url}", "SUCCESS")
        return True
    except requests.RequestException as exc:
        log(f"API server is not reachable: {exc}", "WARNING")
        return True


def main() -> bool:
    checks = {
        "environment": check_environment(),
        "database": check_database(),
        "gemini": check_gemini(),
        "mistral": check_mistral(),
        "server": check_server(),
    }
    print(f"\nTotal: {sum(checks.values())}/{len(checks)} healthy")
    return all(checks.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
