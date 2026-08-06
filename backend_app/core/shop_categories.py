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
    if not category:
        return DEFAULT_CATEGORY

    # Case-insensitive matching
    category_upper = category.upper()

    for valid_cat in SHOP_CATEGORIES:
        if valid_cat.upper() == category_upper:
            return valid_cat

    return DEFAULT_CATEGORY
