"""Fast source-level verification for the backend fixes."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def check_file(name: str, fragments: list[str]) -> bool:
    path = BACKEND_DIR / name
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL {name}: {exc}")
        return False
    missing = [fragment for fragment in fragments if fragment not in content]
    if missing:
        print(f"FAIL {name}: missing {', '.join(repr(item) for item in missing)}")
        return False
    print(f"PASS {name}")
    return True


def main() -> bool:
    checks = [
        check_file("pipeline/embedding_pipeline.py", ["from google import genai", "output_dimensionality=EMBEDDING_DIMENSION", "EmbeddingServiceError"]),
        check_file("pipeline/config.py", ["gemini-2.5-flash-lite", "gemini-2.5-flash"]),
        check_file("pipeline/llm_pipeline.py", ["from mistralai import Mistral", "from mistralai.client import MistralClient", "response_mime_type=\"application/json\""]),
        check_file("pipeline/retrieval_pipeline.py", ["session.execute(", "if threshold is None"]),
        check_file("test_all.py", ["RUN_LIVE_AI_TESTS", "RUN_BENCHMARKS", "timeout=timeout"]),
        check_file("db/database.py", ["connect_timeout", "pool_timeout"]),
    ]
    print(f"\n{sum(checks)}/{len(checks)} checks passed")
    return all(checks)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
