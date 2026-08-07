"""
Voice Inventory Service
Handles AI-powered voice-to-inventory parsing
"""
import google.generativeai as genai
import os
import json
from typing import List, Dict, Any

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key, transport="rest")


def normalize_category_name(category_name: str, existing_categories: List[str]) -> str:
    """
    Normalize category name to match existing categories (case-insensitive)
    
    Args:
        category_name: The category name to normalize
        existing_categories: List of existing category names
    
    Returns:
        Normalized category name
    """
    # Trim and normalize
    normalized = category_name.strip()
    
    # Check for exact match (case-insensitive)
    for existing in existing_categories:
        if existing.lower() == normalized.lower():
            return existing
    
    # No match found, return with proper capitalization
    return normalized.capitalize()


def parse_voice_inventory(
    raw_text: str,
    existing_items: List[Dict[str, Any]],
    existing_categories: List[str]
) -> Dict[str, Any]:
    """
    Parse voice input into structured inventory items
    
    Args:
        raw_text: Raw voice transcription
        existing_items: List of existing inventory items
        existing_categories: List of existing categories
    
    Returns:
        Structured inventory data with categories and items
    """
    
    # Build context about existing inventory
    inventory_context = _build_inventory_context(existing_items, existing_categories)
    
    # Create AI prompt (simplified for better reliability)
    prompt = f"""You are an inventory parser for a Kirana store in India.

Parse this voice input into structured inventory items:
"{raw_text}"

EXISTING CATEGORIES: {', '.join(existing_categories) if existing_categories else 'None'}

RULES:
1. Look for "category <name>" to group items
2. Extract item name, price (with rs/rupees), and unit (kg/litre/plate/etc)
3. If no category mentioned, use "Other"
4. Normalize units: kilo→kg, litre→litre, plate→plate

EXAMPLE INPUT: "category anaaj gehun 25 rs kilo, bajra 30 rupees kg"
EXAMPLE OUTPUT:
{{
  "categories": [
    {{
      "name": "Anaaj",
      "items": [
        {{"name": "Gehun", "price": 25, "unit": "kg", "is_existing": false, "aliases": ["गेहूं", "Wheat"]}},
        {{"name": "Bajra", "price": 30, "unit": "kg", "is_existing": false, "aliases": ["बाजरा", "Pearl Millet"]}}
      ]
    }}
  ],
  "raw_text": "{raw_text}"
}}

Return ONLY valid JSON. No explanation."""

    # Try multiple Gemini models
    candidate_models = [
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001"
    ]

    last_error = ""
    for model_name in candidate_models:
        try:
            print(f"[INFO] Trying model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            result_text = response.text.strip()
            print(f"[DEBUG] Raw AI response: {result_text[:200]}...")
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            try:
                parsed_data = json.loads(result_text)
            except json.JSONDecodeError as je:
                print(f"[ERROR] JSON parse error: {je}")
                print(f"   Attempted to parse: {result_text[:500]}")
                raise
            
            # Post-process: Normalize category names and check for existing items
            if 'categories' in parsed_data:
                for category in parsed_data['categories']:
                    if 'name' in category:
                        category['name'] = normalize_category_name(
                            category['name'],
                            existing_categories
                        )
                    
                    # Check each item against existing inventory
                    if 'items' in category:
                        for item in category['items']:
                            _mark_existing_item(item, existing_items)
            
            print(f"[OK] Parsed voice inventory: {len(parsed_data.get('categories', []))} categories")
            
            # Debug: Print parsed items
            for cat in parsed_data.get('categories', []):
                print(f"   Category: {cat.get('name')}")
                for item in cat.get('items', []):
                    existing_marker = " (EXISTING)" if item.get('is_existing') else " (NEW)"
                    print(f"      - {item.get('name')}: ₹{item.get('price')}/{item.get('unit')}{existing_marker}")
            
            return parsed_data
            
        except Exception as e:
            print(f"[WARN] {model_name} failed: {e}")
            import traceback
            traceback.print_exc()
            last_error = str(e)
            continue
    
    # All models failed - return fallback
    print(f"[ERROR] All models failed. Last error: {last_error}")
    print(f"   Raw text was: {raw_text}")
    return {
        "categories": [{
            "name": "Other",
            "items": [{
                "name": "Parse Error - Check Logs",
                "price": 0,
                "unit": "kg",
                "is_existing": False,
                "aliases": [f"Error: {last_error[:100]}"]
            }]
        }],
        "raw_text": raw_text,
        "error": last_error
    }


def _mark_existing_item(item: Dict[str, Any], existing_items: List[Dict[str, Any]]) -> None:
    """
    Check if item exists in inventory and mark it with old price
    Modifies item dict in-place
    
    Args:
        item: Parsed item dict from AI
        existing_items: List of existing inventory items
    """
    item_name = item.get('name', '').lower().strip()
    
    # Search for matching item (case-insensitive name match)
    for existing in existing_items:
        existing_names = existing.get('names', [])
        
        # Check if any name matches
        for existing_name in existing_names:
            if existing_name.lower().strip() == item_name:
                # Found match - mark as existing and store old price
                item['is_existing'] = True
                item['old_price'] = existing.get('price', 0)
                item['old_unit'] = existing.get('unit', 'kg')
                item['existing_id'] = existing.get('id', '')
                
                print(
                    f"   [INFO] Found existing item: {item_name} "
                    f"(Rs.{item['old_price']}/{item['old_unit']} -> Rs.{item.get('price')}/{item.get('unit')})"
                )
                return
    
    # Not found - mark as new
    item['is_existing'] = False
    item['old_price'] = None


def _build_inventory_context(items: List[Dict[str, Any]], categories: List[str]) -> str:
    """Build context string about existing inventory"""
    
    context_parts = []
    
    # Add categories
    if categories:
        context_parts.append(f"Existing Categories: {', '.join(categories)}")
    
    # Add sample items (limit to 20 for context size)
    if items:
        sample_items = items[:20]
        items_str = []
        for item in sample_items:
            names = item.get('names', [])
            name = names[0] if names else 'Unknown'
            price = item.get('price', 0)
            unit = item.get('unit', 'kg')
            category = item.get('category', 'Other')
            items_str.append(f"{name} (₹{price}/{unit}) in {category}")
        
        context_parts.append(f"Sample Existing Items:\n" + "\n".join(items_str))
    
    return "\n\n".join(context_parts) if context_parts else "No existing inventory"
