"""Test Mistral with LangChain"""
import os
from dotenv import load_dotenv

load_dotenv("backend_app/.env")

# Test Mistral via LangChain
mistral_key = os.getenv("MISTRAL_API_KEY")
print(f"Mistral API Key: {'✓ Found' if mistral_key else '✗ Missing'}")

if mistral_key:
    try:
        from langchain_mistralai import ChatMistralAI
        
        print("\n1. Initializing Mistral LLM via LangChain...")
        llm = ChatMistralAI(
            model="mistral-large-latest",
            mistral_api_key=mistral_key,
            temperature=0.1,
            max_tokens=100,
        )
        print("   ✓ Mistral LLM initialized")
        
        print("\n2. Testing simple prompt...")
        response = llm.invoke("Say 'hello' in JSON format: {\"message\": \"hello\"}")
        print(f"   ✓ Response: {response.content}")
        
        print("\n✅ Mistral is working with LangChain!")
        
    except ImportError as e:
        print(f"\n✗ LangChain Mistral not installed: {e}")
        print("   Run: pip install langchain-mistralai")
    except Exception as e:
        print(f"\n✗ Mistral failed: {e}")
else:
    print("\n✗ Cannot test - MISTRAL_API_KEY not set in .env")

print("\n" + "="*60)
print("TO FIX ON RENDER:")
print("1. Go to https://dashboard.render.com")
print("2. Click 'dead-pixel-vyamit' service")
print("3. Click 'Environment' tab")
print("4. Add:")
print(f"   MISTRAL_API_KEY = {mistral_key}")
print("5. Save and wait for redeploy")
print("="*60)
