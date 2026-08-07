import google.generativeai as genai

import os
import json
from app.db.models import Item
from typing import List

# 1. Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("\n[ERROR] GEMINI_API_KEY is not set. Voice AI will return errors until it is configured.\n")
else:
    genai.configure(api_key=api_key, transport="rest")

class AIService:
    def __init__(self):
        # EXACT MODELS FROM YOUR LIST (Prioritizing Lite for better quota)
        self.candidate_models = [
            "gemini-2.5-flash",          # Try this first (Latest & Fast)
            "gemini-flash-latest",       # Alias for the current stable flash
            "gemini-2.0-flash",          # Powerful but strict quota
            "gemini-2.0-flash-001"       # Alternative version
        ]

    def _build_vyamit_prompt(
        self, user_text: str, inventory: List[Item], shop_category: str = "General"
    ) -> str:
        """Master prompt (inventory + rules + JSON schema) — shared with hybrid pipeline."""
        print(f"\n[INFO] Processing voice: {user_text}")
        print(f"[INFO] Shop category (AI context): {shop_category}")
        
        # CRITICAL: Filter inventory to only include items with price > 0
        filtered_inventory = [item for item in inventory if item.price > 0]
        print(f"[INFO] Total inventory items: {len(inventory)}")
        print(f"[INFO] Items with price > 0: {len(filtered_inventory)}")
        
        # Prepare Inventory with names array support
        inventory_list = []
        for item in filtered_inventory:
            # Parse names from JSON string
            names_array = json.loads(item.names) if isinstance(item.names, str) else item.names
            inventory_list.append({
                "names": names_array,
                "price": item.price,
                "unit": item.unit,
                "category": item.category
            })
        
        inventory_json = json.dumps(inventory_list, ensure_ascii=False)
        
        return f"""You are Vyamit AI, a female voice assistant for "Vyamit AI App". detect the language user is speaking and Answer ONLY in that language  but use Latin Script (Hinglish/Roman script) for giving the billing items to the app that are going to print.  use Devanagari script only for the response question or answer the the query of user .
also give response to user any general queries in short 
SHOP TYPE (mandatory context — this merchant runs a "{shop_category}" business):
- Use this to interpret vague product names and typical units (e.g. Dairy → milk, dahi, paneer, butter; Kirana → general groceries; Hardware → tools, fasteners, building supplies; Stationary → pens, notebooks; Clothing → garments, sizes; Doctor → medicines/clinic supplies where applicable; General → mixed retail).
- Prefer terminology and defaults that match this shop type when the user is unclear.
- Do not refuse valid items solely because they are more typical of another shop type if the user clearly asked for them.

PERSONALITY:
- You are a helpful female AI assistant named Vyamit AI
- Respond to greetings warmly: "Namaste! Main Vyamit AI hoon, aapki sahayak."
- If asked who you are: "Main Vyamit AI hoon, aapki ki voice assistant."
- Be friendly and conversational in Hinglish or the local user language  (Latin script only)
- Always give response in short sentence 

CUSTOMER NAME EXTRACTION:
- If user says "customer [name]" or "naam [name]" or mentions a person's name, extract it
- Examples: "customer raju charde", "naam mohan hai", "ramesh ke liye"
- If NO customer name mentioned, use "Walk-in" as default
- Customer name should be in the "customer_name" field

INVENTORY (Only items with configured prices): {inventory_json}
USER SAID: "{user_text}"

CRITICAL RULES FOR PRICE HANDLING:
1. If user mentions price with item (e.g., "1kg chawal 120 rs kilo" or "5rs wali 6 maggie packet"):
   - EXTRACT the price from user's speech
   - CALCULATE total: quantity × price
   - ADD to bill immediately with that price
   - Example: "5rs wali 6 maggie" → 6 qty, ₹5 rate, ₹30 total
   - Example: "1kg chawal 120 rs kilo" → 1kg qty, ₹120 rate, ₹120 total

2. If item is in inventory (check all name variations):
   - Use inventory price
   - Calculate total correctly

3. If item NOT in inventory AND user did NOT mention price:
   - Ask: "[Item name] ki keemat kya hai?"
   - Return type: "ERROR" with this message

4. Match quantities correctly (1 kg, 2 litre, 5 pieces, etc.)

5. For greetings (hi, hello, namaste):
   - Respond warmly in Hinglish
   - Return type: "GREETING"

OUTPUT JSON FORMAT:
{{
  "type": "BILL" or "ERROR" or "GREETING",
  "customer_name": "Customer Name or Walk-in",
  "items": [ {{"name": "ItemName", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}} ],
  "msg": "Response in Hinglish (Latin script only, NO Devanagari, answer in short)",
  "should_stop": false
}}

if everything is fine with quantity , price and item and you have no questions then give response msg as Saaman Bill mein jod diya gaya hai do not read the whole item list price and all

EXAMPLES:
- User: "customer raju charde 5rs wali 6 maggie packet" → {{"type": "BILL", "customer_name": "Raju Charde", "items": [{{"name": "Maggie", "qty_display": "6pic", "rate": 5.0, "total": 30.0, "unit": "pic"}}], "msg": "Raju Charde ke liye 6 Maggie packet bill mein add kar diya"}}
- User: "1kg chawal 120 rs kilo" → {{"type": "BILL", "customer_name": "Walk-in", "items": [{{"name": "Chawal", "qty_display": "1kg", "rate": 120.0, "total": 120.0, "unit": "kg"}}], "msg": "Saaman Bill mein jod diya gaya hai"}}
- User: "hello" → {{"type": "GREETING", "customer_name": "Walk-in", "items": [], "msg": "Namaste! Main Vyamit AI hoon. Kaise madad kar sakti hoon?"}}
- User: "aam" (not in inventory, no price) → {{"type": "ERROR", "customer_name": "Walk-in", "items": [], "msg": "Aam ki keemat kya hai?"}}"""

    def run_mistral_primary(self, prompt: str):
        """Run Mistral AI as Primary AI model."""
        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_api_key:
            return None
            
        try:
            from mistralai import Mistral
        except ImportError:
            Mistral = None

        if Mistral is None:
            return None

        try:
            print("[INFO] Trying Primary AI: Mistral AI (mistral-large-latest)...")
            client = Mistral(api_key=mistral_api_key)
            
            # Request response from Mistral
            response = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            print("[OK] Primary AI (Mistral) succeeded.")
            
            clean_text = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"[WARN] Primary AI (Mistral) failed: {e}")
            return None

    def run_gemini_only(self, prompt: str):
        """Run the existing Gemini candidate-model loop only (used by hybrid + default path)."""
        last_error = ""
        for model_name in self.candidate_models:
            try:
                print(f"[INFO] Trying model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                print(f"[OK] Model '{model_name}' succeeded.")
                
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
                
            except Exception as e:
                print(f"[WARN] {model_name} failed: {e}")
                last_error = str(e)
                continue  # Try the next model
        
        print(f"\n[ERROR] All Gemini candidate models failed. Last error: {last_error}\n")
        return {
            "type": "ERROR",
            "items": [],
            "msg": "सिस्टम त्रुटि: कृपया बाद में पुनः प्रयास करें।", 
            "should_stop": False
        }

    def process_voice_command(
        self, user_text: str, inventory: List[Item], shop_category: str = "General"
    ):
        prompt = self._build_vyamit_prompt(user_text, inventory, shop_category=shop_category)
        
        # 1. Primary AI: Mistral
        mistral_res = self.run_mistral_primary(prompt)
        if mistral_res:
            return mistral_res
            
        # 2. Fallback AI: Gemini
        print("[INFO] Fallback AI: Gemini initiating...")
        return self.run_gemini_only(prompt)
