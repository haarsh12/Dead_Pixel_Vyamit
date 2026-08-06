"""Inventory-aware voice billing orchestration.

This module is the clean replacement for the legacy ``ai_service`` and the
large WebSocket route in the reference application.  It keeps the provider
integration inside the existing LLM pipeline and owns the stable response
contract consumed by the Flutter voice screen.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List

from pipeline.llm_pipeline import LLMPipeline, llm_pipeline


logger = logging.getLogger(__name__)

_VALID_RESPONSE_TYPES = {"BILL", "QUERY", "ERROR"}
_MAX_CONTEXT_ITEMS = 50


class VoiceService:
    """Translate a voice command into the application's bill response shape."""

    def __init__(self, pipeline: LLMPipeline | None = None) -> None:
        self._pipeline = pipeline or llm_pipeline

    @staticmethod
    def _primary_name(item: Dict[str, Any]) -> str:
        names = item.get("names", [])
        if isinstance(names, str):
            try:
                names = json.loads(names)
            except json.JSONDecodeError:
                names = [names]
        if isinstance(names, list) and names:
            return str(names[0]).strip()
        return "Unknown"

    @classmethod
    def _inventory_context(cls, inventory: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return a compact, safe inventory projection for the model prompt."""
        context: List[Dict[str, Any]] = []
        for item in inventory:
            if len(context) >= _MAX_CONTEXT_ITEMS:
                break
            try:
                price = float(item.get("price", 0))
            except (TypeError, ValueError):
                continue
            if price < 0:
                continue
            context.append(
                {
                    "name": cls._primary_name(item)[:100],
                    "aliases": item.get("names", []) if isinstance(item.get("names"), list) else [],
                    "price": price,
                    "unit": str(item.get("unit") or "unit")[:30],
                    "category": str(item.get("category") or "General")[:60],
                }
            )
        return context

    @classmethod
    def _build_prompt(
        cls, text: str, inventory: Iterable[Dict[str, Any]], shop_category: str
    ) -> str:
        inventory_json = json.dumps(cls._inventory_context(inventory), ensure_ascii=False)
        user_text = json.dumps(text, ensure_ascii=False)
        category = str(shop_category or "General")[:60]
        return f"""You are Vyamit AI, a concise billing assistant for a {category} shop.

The customer said: {user_text}

Available inventory (use its price when an item matches):
{inventory_json}

Return JSON only, with exactly this shape:
{{
  "type": "BILL" | "QUERY" | "ERROR",
  "customer_name": "name or empty string",
  "items": [{{
    "name": "item name",
    "qty": number,
    "qty_display": "for example 2kg",
    "unit": "kg/litre/piece",
    "rate": number,
    "total": number
  }}],
  "msg": "short helpful reply in the customer's language",
  "should_stop": false
}}

Rules:
- Create BILL only when the requested item, quantity, and price are known.
- If an item is in inventory, use its listed price. Do not invent a price.
- For a missing price, return ERROR with an empty items array and ask for it.
- For greetings or price questions, return QUERY with an empty items array.
- ``total`` must equal ``qty * rate``. Do not include markdown or extra keys."""

    @staticmethod
    def _number(value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if number >= 0 else default

    @classmethod
    def _normalise_item(cls, item: Any) -> Dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name") or item.get("item_name") or item.get("en") or "").strip()
        if not name:
            return None
        quantity = cls._number(item.get("qty", item.get("quantity", 1)), 1.0)
        if quantity == 0:
            return None
        rate = cls._number(item.get("rate", item.get("price", item.get("unit_price", 0))), 0.0)
        total = cls._number(item.get("total", item.get("line_total", quantity * rate)), quantity * rate)
        unit = str(item.get("unit") or "unit").strip()[:30] or "unit"
        quantity_display = str(item.get("qty_display") or f"{quantity:g}{unit}").strip()[:40]
        return {
            "name": name[:100],
            "en": str(item.get("en") or name)[:100],
            "hi": str(item.get("hi") or name)[:100],
            "qty": quantity,
            "qty_display": quantity_display,
            "unit": unit,
            "rate": rate,
            "total": round(total, 2),
        }

    @classmethod
    def normalise_response(cls, response: Any) -> Dict[str, Any]:
        """Validate provider output before it reaches HTTP or WebSocket clients."""
        if not isinstance(response, dict):
            return {
                "type": "ERROR",
                "customer_name": "",
                "items": [],
                "msg": "I could not understand that request. Please try again.",
                "should_stop": False,
            }

        response_type = str(response.get("type") or "ERROR").upper()
        if response_type not in _VALID_RESPONSE_TYPES:
            response_type = "ERROR"
        items = [
            normalised
            for normalised in (cls._normalise_item(item) for item in response.get("items", []))
            if normalised is not None
        ]
        if response_type == "BILL" and not items:
            response_type = "ERROR"

        message = str(response.get("msg") or "Please try again.").strip()[:500]
        customer_name = str(response.get("customer_name") or "").strip()[:80]
        return {
            "type": response_type,
            "customer_name": customer_name,
            "items": items if response_type == "BILL" else [],
            "msg": message,
            "should_stop": bool(response.get("should_stop", False)),
        }

    def process(self, text: str, inventory: Iterable[Dict[str, Any]], shop_category: str) -> Dict[str, Any]:
        """Run the configured LLM pipeline and expose a consistent voice result."""
        prompt = self._build_prompt(text, inventory, shop_category)
        response, duration, model = self._pipeline.invoke(prompt)
        result = self.normalise_response(response)
        # Model metadata is useful for observability but contains no prompt,
        # inventory, token, or provider error details.
        result["metadata"] = {"model_used": model, "duration_ms": round(duration * 1000, 2)}
        logger.info("Voice request completed type=%s model=%s", result["type"], model)
        return result


voice_service = VoiceService()
