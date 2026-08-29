import re

# Olist IDs (order_id, product_id, customer_id, seller_id) are 32-char
# lowercase hex strings. Anything that doesn't match this shape is
# rejected before it ever reaches a SQL query.
ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def is_valid_id(value) -> bool:
    """True only for well-formed 32-char hex Olist IDs."""
    if not isinstance(value, str):
        return False
    return bool(ID_PATTERN.match(value.strip().lower()))


def clean_id(value) -> str:
    """Normalize an ID (strip whitespace, lowercase)."""
    return value.strip().lower() if isinstance(value, str) else value


def is_valid_category(value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    # category names in the DB are lowercase_with_underscores
    return bool(re.match(r"^[a-z0-9_]+$", value.strip().lower()))


def clean_category(value) -> str:
    return value.strip().lower().replace(" ", "_") if isinstance(value, str) else value


def is_valid_price(value) -> bool:
    try:
        return float(value) >= 0
    except (TypeError, ValueError):
        return False


def is_valid_limit(value, max_limit: int = 25) -> bool:
    try:
        n = int(value)
        return 1 <= n <= max_limit
    except (TypeError, ValueError):
        return False
