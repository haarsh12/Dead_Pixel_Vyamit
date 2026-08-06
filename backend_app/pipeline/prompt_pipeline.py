"""
Prompt Pipeline - Context Assembly and Prompt Building
Structures retrieved context into effective prompts
"""
from typing import List, Dict, Any, Optional
import json


class PromptPipeline:
    """Builds structured prompts for LLM"""
    
    @staticmethod
    def build_rag_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        analytics: Optional[Dict[str, Any]],
        customers: List[Dict[str, Any]],
        shop_category: str = "General"
    ) -> str:
        """
        Build complete RAG prompt with all context
        
        Args:
            user_query: User's question
            items: Retrieved similar items
            analytics: Business analytics
            customers: Similar customers
            shop_category: Shop type
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # System context
        prompt_parts.append(f"""You are an AI assistant for a {shop_category} shop.
Your role is to help with billing, inventory queries, and business insights.

IMPORTANT RESPONSE FORMAT:
You MUST respond in JSON format with this exact structure:
{{
    "type": "BILL" | "QUERY" | "ERROR",
    "items": [list of items if type is BILL, empty otherwise],
    "msg": "conversational message for the user",
    "should_stop": false
}}

For BILL type, items array should contain:
[{{"name": "item name", "quantity": number, "unit": "kg/litre/etc", "price": number}}]

For QUERY type, provide helpful information in the msg field.
For ERROR type, explain the issue politely.""")
        
        # User query
        prompt_parts.append(f"\nUSER QUERY: {user_query}\n")
        
        # Items context
        if items:
            prompt_parts.append("AVAILABLE INVENTORY:")
            for item in items[:5]:  # Top 5
                names = json.loads(item['names'])
                primary_name = names[0] if names else "Unknown"
                prompt_parts.append(
                    f"- {primary_name} ({item['category']}): "
                    f"₹{item['price']}/{item['unit']} "
                    f"[Relevance: {item['similarity']:.2f}]"
                )
            prompt_parts.append("")
        
        # Analytics context
        if analytics and analytics.get('bill_count', 0) > 0:
            prompt_parts.append("BUSINESS INSIGHTS:")
            prompt_parts.append(
                f"- Last {analytics['period_days']} days: "
                f"{analytics['bill_count']} bills, "
                f"₹{analytics['total_revenue']:.2f} revenue, "
                f"₹{analytics['avg_bill_value']:.2f} avg bill"
            )
            
            if analytics.get('top_items'):
                prompt_parts.append("- Top items:")
                for item in analytics['top_items'][:3]:
                    prompt_parts.append(
                        f"  • {item['name']}: "
                        f"₹{item['total_revenue']:.2f} revenue"
                    )
            prompt_parts.append("")
        
        # Customer context
        if customers:
            prompt_parts.append("SIMILAR CUSTOMERS:")
            for customer in customers[:3]:  # Top 3
                name = customer.get('name') or f"Customer ending {customer['phone_number'][-4:]}"
                prompt_parts.append(
                    f"- {name}: {customer['total_bills']} bills, "
                    f"₹{customer['total_spent']:.2f} spent"
                )
            prompt_parts.append("")
        
        # Instructions
        prompt_parts.append("""Based on the context above, respond to the user's query.
If they're asking for a bill, extract items and quantities from their request.
If they're asking a question, use the context to provide helpful insights.
Always respond in valid JSON format as specified.""")
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def build_simple_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        shop_category: str = "General"
    ) -> str:
        """
        Build simplified prompt (faster, less context)
        
        Args:
            user_query: User's question
            items: Retrieved items
            shop_category: Shop type
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        prompt_parts.append(f"""You are a billing assistant for a {shop_category} shop.
Parse the user's request and respond in JSON format:
{{
    "type": "BILL" | "QUERY" | "ERROR",
    "items": [{{"name": "...", "quantity": ..., "unit": "...", "price": ...}}],
    "msg": "message for user",
    "should_stop": false
}}""")
        
        prompt_parts.append(f"\nUSER: {user_query}\n")
        
        if items:
            prompt_parts.append("INVENTORY:")
            for item in items[:5]:
                names = json.loads(item['names'])
                primary_name = names[0] if names else "Unknown"
                prompt_parts.append(
                    f"- {primary_name}: ₹{item['price']}/{item['unit']}"
                )
        
        prompt_parts.append("\nRespond in JSON format:")
        
        return "\n".join(prompt_parts)
