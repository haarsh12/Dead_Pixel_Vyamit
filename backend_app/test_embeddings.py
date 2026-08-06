"""Opt-in live checks for Gemini embeddings.

Set RUN_LIVE_AI_TESTS=1 to run these checks. They call a billable external API
and therefore are intentionally excluded from the default test run.
"""

import math
import os

from dotenv import load_dotenv

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message: str, level: str = "INFO") -> None:
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}[level]
    print(f"{color}[{level}]{RESET} {message}")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if denominator == 0:
        raise ValueError("Cannot calculate similarity for a zero embedding.")
    return sum(a * b for a, b in zip(left, right)) / denominator


def test_embedding_api() -> bool:
    """Verify single and batched calls return 768-dimensional vectors."""
    try:
        from pipeline.embedding_pipeline import EMBEDDING_DIMENSION, embedding_pipeline

        query_embedding, elapsed = embedding_pipeline.generate_query_embedding("sugar चीनी 1kg")
        document_embeddings = embedding_pipeline.generate_embeddings_batch(
            ["Sugar 1kg", "Salt 500g", "Rice 5kg"]
        )
        if len(query_embedding) != EMBEDDING_DIMENSION:
            log(f"Unexpected query dimension: {len(query_embedding)}", "ERROR")
            return False
        if len(document_embeddings) != 3 or any(
            len(embedding) != EMBEDDING_DIMENSION for embedding in document_embeddings
        ):
            log("Batch response does not contain three 768D embeddings", "ERROR")
            return False
        log(f"Gemini generated 768D query and batch embeddings in {elapsed * 1000:.0f}ms", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Gemini embedding check failed: {exc}", "ERROR")
        return False


def test_embedding_quality() -> bool:
    """Confirm multilingual sugar search ranks Sugar above clear distractors."""
    try:
        from pipeline.embedding_pipeline import embedding_pipeline

        query = embedding_pipeline.generate_embedding("mujhe chini sugar chahiye")
        names = ["Sugar 1kg", "Salt 500g", "Rice 5kg"]
        embeddings = embedding_pipeline.generate_embeddings_batch(names)
        ranked = sorted(
            ((name, cosine_similarity(query, embedding)) for name, embedding in zip(names, embeddings)),
            key=lambda entry: entry[1],
            reverse=True,
        )
        best_name, best_score = ranked[0]
        log("Similarity ranking: " + ", ".join(f"{name}={score:.3f}" for name, score in ranked))
        if best_name != "Sugar 1kg":
            log(f"Expected Sugar 1kg as the best result, got {best_name}", "ERROR")
            return False
        log(f"Semantic quality check passed ({best_score:.3f})", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Embedding quality check failed: {exc}", "ERROR")
        return False


def main() -> bool:
    if os.getenv("RUN_LIVE_AI_TESTS") != "1":
        log("SKIPPED: set RUN_LIVE_AI_TESTS=1 to run Gemini integration checks.", "WARNING")
        return True
    if not os.getenv("GEMINI_API_KEY", "").strip():
        log("GEMINI_API_KEY is required when RUN_LIVE_AI_TESTS=1.", "ERROR")
        return False

    results = {
        "embedding_api": test_embedding_api(),
        "semantic_quality": test_embedding_quality(),
    }
    print(f"\nTotal: {sum(results.values())}/{len(results)} passed")
    return all(results.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
