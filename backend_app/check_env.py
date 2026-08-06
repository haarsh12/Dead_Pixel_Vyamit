"""Check backend configuration without exposing secret values."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(ENV_PATH, override=False)

print("\n" + "=" * 60)
print("ENVIRONMENT VARIABLE CHECK")
print("=" * 60)
print(f"\nBackend directory: {BACKEND_DIR}")
print(f".env file: {'found' if ENV_PATH.exists() else 'not found'}")
print("\nCONFIGURATION:")

settings = {
    "DATABASE_URL": "required for database tests and the API",
    "SECRET_KEY": "required for secure production JWTs",
    "GEMINI_API_KEY": "optional unless live AI tests/features are used",
    "MISTRAL_API_KEY": "optional unless Mistral is used",
    "OTP_DEMO_MODE": "optional local-development setting",
}

for key, purpose in settings.items():
    state = "configured" if os.getenv(key, "").strip() else "not configured"
    print(f"- {key:20} {state} ({purpose})")

print("\nDIAGNOSIS:")
if not os.getenv("DATABASE_URL", "").strip():
    print("- DATABASE_URL must be set before the database and RAG checks can run.")
elif not ENV_PATH.exists():
    print("- DATABASE_URL is set in the shell, but no local .env file was found.")
else:
    print("- Local configuration is ready for: python test_all.py")

if os.getenv("RUN_LIVE_AI_TESTS") == "1":
    print("- Live AI tests are enabled and will validate configured provider keys.")
else:
    print("- Live AI tests are disabled (set RUN_LIVE_AI_TESTS=1 after adding valid keys).")

print("\nSecret values are intentionally never printed.\n")
