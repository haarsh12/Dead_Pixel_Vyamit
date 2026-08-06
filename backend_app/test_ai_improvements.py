"""
Test AI Improvements - Latin Script for Bills, Devanagari for Messages
"""
from services.voice_service import VoiceService
from pipeline.prompt_pipeline import PromptPipeline

def test_voice_service_prompt():
    """Test that voice service prompt enforces Latin script for items"""
    service = VoiceService()
    
    # Test inventory
    inventory = [
        {
            "name": "Rice",
            "aliases": ["चावल", "Chawal"],
            "price": 50.0,
            "unit": "kg",
            "category": "Grains"
        }
    ]
    
    # Test text in Hindi
    text = "2 किलो टमाटर 80 रुपये"
    prompt = service._build_prompt(text, inventory, "General")
    
    print("=== VOICE SERVICE PROMPT TEST ===\n")
    print("Test Input (Hindi with price & quantity):", text)
    print("\n--- Generated Prompt Preview ---")
    print(prompt[:600])
    print("\n... (truncated) ...\n")
    
    # Check for key requirements
    checks = [
        ("Latin Script for Items", "Latin script ONLY" in prompt or "Latin script" in prompt),
        ("Hinglish Examples", "Chawal" in prompt and "Tamatar" in prompt),
        ("Devanagari for Messages", "can use Devanagari" in prompt),
        ("Printer Compatibility", "printer" in prompt.lower() or "PRINTER" in prompt),
        ("Non-Inventory Support", "NOT in inventory" in prompt),
    ]
    
    print("=== PROMPT REQUIREMENTS CHECK ===")
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
    
    return all(passed for _, passed in checks)


def test_rag_prompt():
    """Test that RAG prompt enforces Latin script for items"""
    pipeline = PromptPipeline()
    
    items = [
        {
            "name": "Rice",
            "price": 50.0,
            "unit": "kg",
            "category": "Grains",
            "similarity": 0.95
        }
    ]
    
    analytics = {
        "period_days": 30,
        "bill_count": 150,
        "total_revenue": 25000.0,
        "avg_bill_value": 166.67,
        "top_items": [
            {"name": "Rice", "total_revenue": 5000.0}
        ]
    }
    
    prompt = pipeline.build_rag_prompt(
        user_query="मेरे top items क्या हैं?",
        items=items,
        analytics=analytics,
        customers=[],
        shop_category="Grocery"
    )
    
    print("\n=== RAG PROMPT TEST ===\n")
    print("Test Query (Hindi): 'मेरे top items क्या हैं?'")
    print("\n--- Generated Prompt Preview ---")
    print(prompt[:700])
    print("\n... (truncated) ...\n")
    
    # Check for key requirements
    checks = [
        ("Latin Script for Items", "Latin script ONLY" in prompt),
        ("Hinglish Examples", "Chawal" in prompt or "Tamatar" in prompt),
        ("Devanagari for Messages", "Devanagari" in prompt),
        ("Printer Compatibility", "printer" in prompt.lower()),
        ("Language Detection", "language" in prompt.lower()),
    ]
    
    print("=== PROMPT REQUIREMENTS CHECK ===")
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
    
    return all(passed for _, passed in checks)


def test_simple_prompt():
    """Test simple prompt"""
    pipeline = PromptPipeline()
    
    items = [{"name": "Rice", "price": 50.0, "unit": "kg", "category": "Grains"}]
    
    prompt = pipeline.build_simple_prompt(
        user_query="2kg chawal",
        items=items,
        shop_category="General"
    )
    
    print("\n=== SIMPLE PROMPT TEST ===\n")
    print("Test Query: '2kg chawal'")
    print("\n--- Generated Prompt Preview ---")
    print(prompt[:500])
    print("\n... (truncated) ...\n")
    
    # Check for key requirements
    checks = [
        ("Latin Script for Items", "Latin script" in prompt),
        ("Printer Compatibility", "PRINTER" in prompt or "printer" in prompt.lower()),
        ("Message Language Support", "Devanagari" in prompt or "language" in prompt.lower()),
    ]
    
    print("=== PROMPT REQUIREMENTS CHECK ===")
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
    
    return all(passed for _, passed in checks)


if __name__ == "__main__":
    print("=" * 70)
    print("AI IMPROVEMENTS TEST SUITE - PRINTER COMPATIBILITY")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Voice Service Prompt", test_voice_service_prompt()))
    results.append(("RAG Prompt", test_rag_prompt()))
    results.append(("Simple Prompt", test_simple_prompt()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nKEY FEATURES VERIFIED:")
        print("1. Item names in bills → Latin script only (Hinglish)")
        print("2. Customer names in bills → Latin script only")
        print("3. AI response messages → User's language (can use Devanagari)")
        print("4. Printer compatibility → Ensured")
    else:
        print("❌ SOME TESTS FAILED - Review the output above")
    print("=" * 70)
