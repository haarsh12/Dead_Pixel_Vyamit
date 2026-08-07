"""
Prompt Pipeline - Context Assembly & Prompt Building
Merges all retrieved contexts into a structured LLM prompt
"""

from typing import Dict, List, Any, Optional
import json


class PromptPipeline:
    """
    Assembles retrieved contexts into a structured prompt for the LLM
    """
    
    @staticmethod
    def build_rag_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        analytics: Dict[str, Any],
        customers: List[Dict[str, Any]],
        shop_category: str = "General"
    ) -> str:
        """
        Build a comprehensive RAG prompt with all context
        
        Sections:
        1. User Query
        2. Relevant Inventory Items
        3. Business Analytics Metrics
        4. Customer History Context
        5. System Instructions
        """
        
        prompt_parts = []
        
        # ===== SYSTEM IDENTITY =====
        prompt_parts.append(
            "You are Vyamit AI, a female voice assistant for shop owners. "
            "You help with billing, inventory queries, business insights, and customer information. "
            "Respond in the same language as the user query (Hindi/English/Hinglish). "
            "Use Devanagari script for Hindi, Latin script for English/Hinglish."
        )
        
        # ===== SHOP CONTEXT =====
        prompt_parts.append(f"\n{'='*60}\nSHOP CONTEXT")
        prompt_parts.append(f"{'='*60}")
        prompt_parts.append(f"Shop Category: {shop_category}")
        prompt_parts.append(
            f"Use this context to interpret vague product names. "
            f"For example, in a '{shop_category}' shop, prioritize items typical of this category."
        )
        
        # ===== USER QUERY =====
        prompt_parts.append(f"\n{'='*60}\nUSER QUERY")
        prompt_parts.append(f"{'='*60}")
        prompt_parts.append(f'"{user_query}"')
        
        # ===== RELEVANT INVENTORY ITEMS =====
        prompt_parts.append(f"\n{'='*60}\nRELEVANT INVENTORY ITEMS (Vector Search Results)")
        prompt_parts.append(f"{'='*60}")
        
        if items:
            prompt_parts.append(f"Found {len(items)} relevant items:")
            for i, item in enumerate(items, 1):
                names = ", ".join(item.get('names', []))
                price = item.get('price', 0.0)
                unit = item.get('unit', '')
                category = item.get('category', '')
                similarity = item.get('similarity', 0.0)
                
                prompt_parts.append(
                    f"{i}. {names} - ₹{price}/{unit} ({category}) [Relevance: {similarity:.2f}]"
                )
        else:
            prompt_parts.append("No matching inventory items found.")
            prompt_parts.append(
                "If the user asks about a product not in inventory, "
                "ask for its price or inform them it's not in stock."
            )
        
        # ===== BUSINESS ANALYTICS =====
        prompt_parts.append(f"\n{'='*60}\nBUSINESS ANALYTICS METRICS")
        prompt_parts.append(f"{'='*60}")
        
        if analytics and analytics.get('summary'):
            summary = analytics['summary']
            stock = analytics.get('stock_status', {})
            
            prompt_parts.append("Financial Summary:")
            prompt_parts.append(f"  • Total Revenue: ₹{summary.get('total_revenue', 0):.2f}")
            prompt_parts.append(f"  • Total Bills: {summary.get('total_bills', 0)}")
            prompt_parts.append(f"  • Average Bill Value: ₹{summary.get('average_bill_value', 0):.2f}")
            prompt_parts.append(f"  • Today's Revenue: ₹{summary.get('today_revenue', 0):.2f}")
            prompt_parts.append(f"  • Today's Bills: {summary.get('today_bills', 0)}")
            
            prompt_parts.append("\nInventory Summary:")
            prompt_parts.append(f"  • Total Items: {summary.get('total_inventory_items', 0)}")
            prompt_parts.append(f"  • Out of Stock: {stock.get('out_of_stock', 0)}")
            prompt_parts.append(f"  • Low Stock: {stock.get('low_stock', 0)}")
            
            top_items = analytics.get('top_selling_items', [])
            if top_items:
                prompt_parts.append("\nTop Selling Items:")
                for i, item in enumerate(top_items[:5], 1):
                    prompt_parts.append(
                        f"  {i}. {item['name']} - {item['quantity']}{item['unit']} sold "
                        f"({item['times_sold']} transactions, ₹{item['revenue']:.2f})"
                    )
            
            categories = analytics.get('category_breakdown', [])
            if categories:
                prompt_parts.append("\nCategory Performance:")
                for cat in categories[:5]:
                    prompt_parts.append(
                        f"  • {cat['category']}: ₹{cat['revenue']:.2f} "
                        f"({cat['quantity']} units sold)"
                    )
        else:
            prompt_parts.append("No analytics data available.")
        
        # ===== CUSTOMER HISTORY =====
        prompt_parts.append(f"\n{'='*60}\nCUSTOMER HISTORY CONTEXT")
        prompt_parts.append(f"{'='*60}")
        
        if customers:
            prompt_parts.append(f"Found {len(customers)} relevant customers:")
            for i, customer in enumerate(customers, 1):
                name = customer.get('customer_name', 'Unknown')
                phone = customer.get('customer_phone', 'N/A')
                bill_count = customer.get('bill_count', 0)
                total_spent = customer.get('total_spent', 0.0)
                last_purchase = customer.get('last_purchase', 'N/A')
                bills = customer.get('bills', [])
                
                prompt_parts.append(f"\n{i}. Customer: {name}")
                prompt_parts.append(f"   Phone: {phone}")
                prompt_parts.append(f"   Total Bills: {bill_count}")
                prompt_parts.append(f"   Total Spent: ₹{total_spent:.2f}")
                prompt_parts.append(f"   Last Purchase: {last_purchase[:10] if last_purchase != 'N/A' else 'N/A'}")
                
                if bills:
                    prompt_parts.append(f"   Recent Purchases:")
                    for j, bill in enumerate(bills[:3], 1):
                        bill_date = bill.get('bill_date', 'N/A')[:10]
                        amount = bill.get('total_amount', 0.0)
                        items_count = bill.get('total_items', 0)
                        
                        prompt_parts.append(f"     • {bill_date}: ₹{amount:.2f} ({items_count} items)")
                        
                        # Show top items from this bill
                        bill_items = bill.get('items', [])
                        if bill_items:
                            item_names = [item.get('name', 'Unknown') for item in bill_items[:3]]
                            prompt_parts.append(f"       Items: {', '.join(item_names)}")
        else:
            prompt_parts.append(
                "No customer history available. "
                "If the user mentions a customer name, extract it for future reference."
            )
        
        # ===== INSTRUCTIONS =====
        prompt_parts.append(f"\n{'='*60}\nINSTRUCTIONS")
        prompt_parts.append(f"{'='*60}")
        
        instructions = """
Based on the above context (Inventory Items, Analytics Metrics, Customer History), respond to the user's query intelligently.

BILLING TASKS:
- If the user is creating a bill, extract items from the "Relevant Inventory Items" section
- Use the exact prices shown in the inventory context
- Calculate totals accurately: quantity × price
- If user mentions a customer name, extract it
- Return JSON format:
{
  "type": "BILL",
  "customer_name": "Customer Name or Walk-in",
  "items": [
    {"name": "ItemName", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}
  ],
  "msg": "Short confirmation in user's language",
  "should_stop": false
}

ANALYTICS QUERIES:
- If user asks about sales, revenue, top items, or business performance
- Use the "Business Analytics Metrics" section above
- Provide accurate numbers from the analytics context
- Be conversational and helpful
- Example: "Aaj ka revenue ₹500 hai, 5 bills bane hain"

CUSTOMER QUERIES:
- If user asks about a specific customer's history
- Use the "Customer History Context" section above
- Provide purchase history, spending patterns, last purchase date
- Example: "Rahul ne total 10 baar kharidari ki hai, ₹5000 kharch kiye hain"

INVENTORY QUERIES:
- If user asks about stock, availability, prices
- Use the "Relevant Inventory Items" section above
- Tell them what's in stock, what's low, what's out
- Example: "Chawal available hai ₹50/kg me"

GENERAL QUERIES & GREETINGS:
- Respond warmly and naturally
- Return type: "GREETING" or "INFO"
- Keep responses short and friendly

ERROR HANDLING:
- If item not in inventory and user didn't mention price, ask for price
- Return type: "ERROR" with appropriate message

LANGUAGE:
- Respond in the same language as the user query
- Use Devanagari for Hindi, Latin script for English/Hinglish
- Keep responses natural and conversational
"""
        
        prompt_parts.append(instructions)
        
        # ===== FINAL PROMPT =====
        return "\n".join(prompt_parts)
    
    @staticmethod
    def build_simple_billing_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        shop_category: str = "General"
    ) -> str:
        """
        Build a simpler prompt for billing-only tasks (faster, less context)
        """
        
        prompt = f"""You are Vyamit AI, a billing assistant for a {shop_category} shop.

USER QUERY: "{user_query}"

AVAILABLE INVENTORY:
"""
        
        if items:
            for i, item in enumerate(items, 1):
                names = ", ".join(item.get('names', []))
                price = item.get('price', 0.0)
                unit = item.get('unit', '')
                
                prompt += f"{i}. {names} - ₹{price}/{unit}\n"
        else:
            prompt += "No matching items found. Ask for price if needed.\n"
        
        prompt += """
TASK:
- Extract billing items from user query
- Match with available inventory above
- Calculate totals: quantity × price
- Return JSON:
{
  "type": "BILL",
  "customer_name": "Walk-in",
  "items": [{"name": "ItemName", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}],
  "msg": "Confirmation message in user's language",
  "should_stop": false
}
"""
        
        return prompt
    
    @staticmethod
    def extract_customer_name(user_query: str) -> Optional[str]:
        """
        Extract customer name from query if mentioned
        Patterns: "customer [name]", "naam [name]", "[name] ke liye"
        """
        query_lower = user_query.lower()
        
        # Pattern 1: "customer raju" or "customer name raju"
        if "customer" in query_lower:
            parts = user_query.split("customer", 1)
            if len(parts) > 1:
                name_part = parts[1].strip().split()[0:3]  # Take first 1-3 words
                return " ".join(name_part).strip()
        
        # Pattern 2: "naam raju" or "naam hai raju"
        if "naam" in query_lower:
            parts = user_query.split("naam", 1)
            if len(parts) > 1:
                name_part = parts[1].replace("hai", "").strip().split()[0:3]
                return " ".join(name_part).strip()
        
        # Pattern 3: "raju ke liye"
        if "ke liye" in query_lower or "keliye" in query_lower:
            parts = user_query.split("ke liye" if "ke liye" in query_lower else "keliye", 1)
            if len(parts) > 0:
                words = parts[0].strip().split()
                if words:
                    return " ".join(words[-2:]).strip()  # Take last 1-2 words before "ke liye"
        
        return None

