"""
Shop Categories Configuration
Predefined categories for shop types
"""

SHOP_CATEGORIES = [
    "Kirana",
    "Dairy",
    "Hardware",
    "General",
    "Stationary",
    "Clothing",
    "Medical",
    "Electronics",
    "Bakery",
    "Restaurant",
    "Other"
]

# Default category
DEFAULT_CATEGORY = "General"


def validate_category(category: str) -> str:
    """
    Validate and return shop category
    
    Args:
        category: Category name
    
    Returns:
        Valid category name or DEFAULT_CATEGORY
    """
    if category and category in SHOP_CATEGORIES:
        return category
    return DEFAULT_CATEGORY
