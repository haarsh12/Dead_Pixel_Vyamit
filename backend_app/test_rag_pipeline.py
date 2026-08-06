"""RAG pipeline checks with optional live-provider coverage."""

import os

from dotenv import load_dotenv
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


def test_prompt_pipeline() -> bool:
    try:
        from pipeline.prompt_pipeline import PromptPipeline

        prompt = PromptPipeline.build_rag_prompt(
            user_query="What are my top selling items?",
            items=[
                {"names": ["Sugar", "चीनी"], "price": 50, "unit": "kg", "category": "Grocery"},
                {"names": '["Rice", "चावल"]', "price": 60, "unit": "kg", "category": "Grocery"},
            ],
            analytics={
                "period_days": 30,
                "bill_count": 150,
                "total_revenue": 50000,
                "avg_bill_value": 333,
                "top_items": [],
            },
            customers=[],
            shop_category="Kirana",
        )
        required_content = ("Sugar", "Rice", "50000.00", "USER QUERY")
        if not all(content in prompt for content in required_content):
            log("Prompt is missing expected context.", "ERROR")
            return False
        log("Prompt builder accepts API and database item shapes", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Prompt pipeline check failed: {exc}", "ERROR")
        return False


def test_retrieval_pipeline() -> bool:
    """Exercise the retrieval SQL without spending a live embedding request."""
    try:
        from db.database import engine
        from db.models import User
        from pipeline.retrieval_pipeline import RetrievalPipeline

        with Session(engine) as session:
            user = session.exec(select(User)).first()
        if user is None:
            log("No user exists; retrieval integration check skipped.", "WARNING")
            return True

        items = RetrievalPipeline(engine).retrieve_items(
            query_embedding=[0.1] * 768,
            user_id=user.id,
            top_k=5,
            threshold=0.0,
        )
        if not isinstance(items, list) or any("id" not in item for item in items):
            log("Retrieval returned an invalid item contract.", "ERROR")
            return False
        log(f"Retrieval SQL completed successfully ({len(items)} results)", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Retrieval pipeline check failed: {exc}", "ERROR")
        return False


def test_error_handling() -> bool:
    try:
        from pipeline.llm_pipeline import LLMPipeline, llm_pipeline

        response, duration, provider = llm_pipeline.invoke("")
        if provider != "error" or duration != 0.0 or not llm_pipeline.validate_response(response):
            log("Empty input did not produce the expected local error response.", "ERROR")
            return False
        parsed = LLMPipeline._parse_json_response("```json\n{\"type\": \"QUERY\"}\n```")
        if parsed["type"] != "QUERY":
            log("JSON code-fence parsing failed.", "ERROR")
            return False
        log("Error handling and JSON parsing work without provider calls", "SUCCESS")
        return True
    except Exception as exc:
        log(f"RAG error handling check failed: {exc}", "ERROR")
        return False


def test_live_rag_flow() -> bool:
    if os.getenv("RUN_LIVE_AI_TESTS") != "1":
        log("SKIPPED: set RUN_LIVE_AI_TESTS=1 for an end-to-end provider check.", "WARNING")
        return True
    try:
        from db.database import engine
        from db.models import User
        from pipeline.embedding_pipeline import embedding_pipeline
        from pipeline.llm_pipeline import llm_pipeline
        from pipeline.prompt_pipeline import PromptPipeline
        from pipeline.retrieval_pipeline import RetrievalPipeline

        with Session(engine) as session:
            user = session.exec(select(User)).first()
        if user is None:
            log("No user exists; live RAG check skipped.", "WARNING")
            return True

        embedding = embedding_pipeline.generate_embedding("I need 2kg sugar")
        items = RetrievalPipeline(engine).retrieve_items(embedding, user.id, top_k=5)
        prompt = PromptPipeline.build_simple_prompt("I need 2kg sugar", items, user.shop_category or "General")
        response, _, model = llm_pipeline.invoke(prompt)
        if not llm_pipeline.validate_response(response) or model == "error":
            log("Live RAG flow did not return a provider response.", "ERROR")
            return False
        log(f"Live RAG flow succeeded using {model}", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Live RAG flow failed: {exc}", "ERROR")
        return False


def main() -> bool:
    results = {
        "prompt": test_prompt_pipeline(),
        "retrieval": test_retrieval_pipeline(),
        "error_handling": test_error_handling(),
        "live_flow": test_live_rag_flow(),
    }
    print(f"\nTotal: {sum(results.values())}/{len(results)} passed")
    return all(results.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
