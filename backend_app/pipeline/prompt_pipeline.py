"""Prompt assembly for billing and retrieval-augmented queries."""

import json
from typing import Any, Dict, List, Optional


class PromptPipeline:
    """Build structured, provider-neutral prompts from retrieved application data."""

    @staticmethod
    def _primary_name(item: Dict[str, Any]) -> str:
        """Extract the preferred inventory name from database or API-shaped data."""
        names = item.get("names", [])
        if isinstance(names, str):
            try:
                names = json.loads(names)
            except json.JSONDecodeError:
                names = [names]
        if isinstance(names, list) and names:
            return str(names[0])
        return "Unknown"

    @staticmethod
    def _format_inventory_item(item: Dict[str, Any], include_similarity: bool) -> str:
        name = PromptPipeline._primary_name(item)
        category = item.get("category", "General")
        price = item.get("price", 0)
        unit = item.get("unit", "unit")
        line = f"- {name} ({category}): ₹{price}/{unit}"
        similarity = item.get("similarity")
        if include_similarity and similarity is not None:
            try:
                line += f" [Relevance: {float(similarity):.2f}]"
            except (TypeError, ValueError):
                # Context should still be useful if a caller supplies an item
                # without a numeric retrieval score.
                pass
        return line

    @staticmethod
    def build_rag_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        analytics: Optional[Dict[str, Any]],
        customers: List[Dict[str, Any]],
        shop_category: str = "General",
    ) -> str:
        """Build the full RAG prompt using optional retrieved context."""
        prompt_parts = [
            f"""You are an AI assistant for a {shop_category} shop.
Your role is to help with billing, inventory queries, and business insights.

Return JSON only, with exactly this structure:
{{
  "type": "BILL" | "QUERY" | "ERROR",
  "items": [{{"name": "item name", "quantity": number, "unit": "kg/litre/etc", "price": number}}],
  "msg": "conversational message for the user",
  "should_stop": false
}}

For QUERY, use an empty items array. For ERROR, explain the issue politely.""",
            f"\nUSER QUERY: {user_query}\n",
        ]

        if items:
            prompt_parts.append("AVAILABLE INVENTORY:")
            prompt_parts.extend(
                PromptPipeline._format_inventory_item(item, include_similarity=True)
                for item in items[:5]
            )
            prompt_parts.append("")

        if analytics and analytics.get("bill_count", 0) > 0:
            prompt_parts.extend(
                [
                    "BUSINESS INSIGHTS:",
                    (
                        f"- Last {analytics.get('period_days', 30)} days: "
                        f"{analytics['bill_count']} bills, "
                        f"₹{analytics.get('total_revenue', 0):.2f} revenue, "
                        f"₹{analytics.get('avg_bill_value', 0):.2f} average bill"
                    ),
                ]
            )
            top_items = analytics.get("top_items", [])
            if top_items:
                prompt_parts.append("- Top items:")
                prompt_parts.extend(
                    f"  • {item.get('name', 'Unknown')}: ₹{item.get('total_revenue', 0):.2f} revenue"
                    for item in top_items[:3]
                )
            prompt_parts.append("")

        if customers:
            prompt_parts.append("SIMILAR CUSTOMERS:")
            for customer in customers[:3]:
                phone = str(customer.get("phone_number", ""))
                name = customer.get("name") or f"Customer ending {phone[-4:] or 'unknown'}"
                prompt_parts.append(
                    f"- {name}: {customer.get('total_bills', 0)} bills, "
                    f"₹{float(customer.get('total_spent', 0)):.2f} spent"
                )
            prompt_parts.append("")

        prompt_parts.append(
            "Use only the supplied context when it is relevant. Always return valid JSON."
        )
        return "\n".join(prompt_parts)

    @staticmethod
    def build_simple_prompt(
        user_query: str,
        items: List[Dict[str, Any]],
        shop_category: str = "General",
    ) -> str:
        """Build a concise inventory-aware billing prompt."""
        prompt_parts = [
            f"""You are a billing assistant for a {shop_category} shop.
Return JSON only:
{{
  "type": "BILL" | "QUERY" | "ERROR",
  "items": [{{"name": "...", "quantity": number, "unit": "...", "price": number}}],
  "msg": "message for user",
  "should_stop": false
}}""",
            f"\nUSER: {user_query}\n",
        ]

        if items:
            prompt_parts.append("INVENTORY:")
            prompt_parts.extend(
                PromptPipeline._format_inventory_item(item, include_similarity=False)
                for item in items[:5]
            )

        prompt_parts.append("\nRespond in JSON format:")
        return "\n".join(prompt_parts)
