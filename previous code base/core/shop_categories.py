"""Canonical shop types for Vyamit merchants (registration + profile + AI context)."""

from typing import List, Optional

ALLOWED_SHOP_CATEGORIES: List[str] = [
    "Kirana",
    "Dairy",
    "Hardware",
    "General",
    "Stationary",
    "Clothing",
    "Doctor",
    "Other",
]


def normalize_shop_category(value: Optional[str]) -> Optional[str]:
    """Return canonical category label or None if invalid."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    lower = s.lower()
    for c in ALLOWED_SHOP_CATEGORIES:
        if c.lower() == lower:
            return c
    return None


def validate_shop_category_required(value: Optional[str]) -> str:
    """For mandatory registration: raises ValueError if invalid."""
    n = normalize_shop_category(value)
    if n is None:
        raise ValueError(
            f"Invalid shop_category. Must be one of: {', '.join(ALLOWED_SHOP_CATEGORIES)}"
        )
    return n
