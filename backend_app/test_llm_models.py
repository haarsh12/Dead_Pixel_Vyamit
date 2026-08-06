"""Opt-in live checks for the configured LLM providers."""

import os

from dotenv import load_dotenv

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

PROMPT = """Return JSON only: {"type":"QUERY","items":[],"msg":"OK","should_stop":false}"""


def log(message: str, level: str = "INFO") -> None:
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}[level]
    print(f"{color}[{level}]{RESET} {message}")


def test_mistral() -> bool | None:
    if not os.getenv("MISTRAL_API_KEY", "").strip():
        log("Mistral is not configured; skipping its provider check.", "WARNING")
        return None
    try:
        from pipeline.llm_pipeline import llm_pipeline

        response, elapsed = llm_pipeline.invoke_mistral(PROMPT)
        if not llm_pipeline.validate_response(response):
            log("Mistral returned an invalid response contract.", "ERROR")
            return False
        log(f"Mistral returned a valid JSON response in {elapsed * 1000:.0f}ms", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Mistral provider check failed: {exc}", "ERROR")
        return False


def test_gemini() -> bool | None:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        log("Gemini is not configured; skipping its provider check.", "WARNING")
        return None
    try:
        from pipeline.llm_pipeline import llm_pipeline

        response, elapsed = llm_pipeline.invoke_gemini(PROMPT)
        if not llm_pipeline.validate_response(response):
            log("Gemini returned an invalid response contract.", "ERROR")
            return False
        log(f"Gemini returned a valid JSON response in {elapsed * 1000:.0f}ms", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Gemini provider check failed: {exc}", "ERROR")
        return False


def test_fallback_pipeline() -> bool:
    try:
        from pipeline.llm_pipeline import llm_pipeline

        response, _, model = llm_pipeline.invoke(PROMPT)
        if not llm_pipeline.validate_response(response):
            log("Fallback pipeline returned an invalid response contract.", "ERROR")
            return False
        log(f"Fallback pipeline response validated (provider: {model})", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Fallback pipeline check failed: {exc}", "ERROR")
        return False


def main() -> bool:
    if os.getenv("RUN_LIVE_AI_TESTS") != "1":
        log("SKIPPED: set RUN_LIVE_AI_TESTS=1 to run LLM integration checks.", "WARNING")
        return True

    provider_results = [test_mistral(), test_gemini()]
    pipeline_result = test_fallback_pipeline()
    ran_provider = any(result is not None for result in provider_results)
    results = [result for result in provider_results if result is not None] + [pipeline_result]
    if not ran_provider:
        log("Configure GEMINI_API_KEY or MISTRAL_API_KEY to run a provider check.", "ERROR")
        return False
    print(f"\nTotal: {sum(results)}/{len(results)} passed")
    return all(results)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
