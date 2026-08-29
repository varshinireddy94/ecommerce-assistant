"""
Predefined, read-only SQL tools for the ShopSphere support assistant.

Rules enforced in this file (see task spec, section "Database Security"):
  * The LLM never writes or sees raw SQL - it only ever picks a tool name
    and JSON parameters (see TOOL_SCHEMAS at the bottom of this file).
  * Every query below is fully parameterized (no string formatting into SQL).
  * Every ID-shaped parameter is validated BEFORE it touches the database.
  * Only the columns actually needed for the customer-facing answer are
    selected/returned - nothing else in the row is exposed.
"""

import sqlite3
from pathlib import Path

from backend.src.validators import (
    is_valid_id,
    clean_id,
    is_valid_category,
    clean_category,
    is_valid_price,
    is_valid_limit,
)

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "ecommerce.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _error(message: str):
    return {"error": message}


# --------------------------------------------------------------------------
# 1. Order status
# --------------------------------------------------------------------------
def get_order_status(order_id: str):
    if not is_valid_id(order_id):
        return _error("invalid_order_id")

    order_id = clean_id(order_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT order_id,
               order_status,
               order_purchase_timestamp,
               order_delivered_customer_date,
               order_estimated_delivery_date
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return _error("order_not_found")

    return {
        "order_id": row["order_id"],
        "status": row["order_status"],
        "purchase_date": row["order_purchase_timestamp"],
        "delivery_date": row["order_delivered_customer_date"],
        "estimated_delivery_date": row["order_estimated_delivery_date"],
    }


# --------------------------------------------------------------------------
# 2. Order items
# --------------------------------------------------------------------------
def get_order_items(order_id: str):
    if not is_valid_id(order_id):
        return _error("invalid_order_id")

    order_id = clean_id(order_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT oi.product_id,
               p.category,
               oi.price,
               oi.freight_value
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return _error("no_items_found")

    return {
        "order_id": order_id,
        "items": [
            {
                "product_id": r["product_id"],
                "category": r["category"],
                "price": r["price"],
                "freight_value": r["freight_value"],
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------
# 3. Order total
# --------------------------------------------------------------------------
def get_order_total(order_id: str):
    if not is_valid_id(order_id):
        return _error("invalid_order_id")

    order_id = clean_id(order_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS item_count,
               SUM(price) AS items_total,
               SUM(freight_value) AS freight_total
        FROM order_items
        WHERE order_id = ?
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None or row["item_count"] == 0:
        return _error("order_not_found")

    items_total = row["items_total"] or 0.0
    freight_total = row["freight_total"] or 0.0

    return {
        "order_id": order_id,
        "item_count": row["item_count"],
        "items_total": round(items_total, 2),
        "freight_total": round(freight_total, 2),
        "grand_total": round(items_total + freight_total, 2),
    }


# --------------------------------------------------------------------------
# 4. Delivery details
# --------------------------------------------------------------------------
def get_delivery_details(order_id: str):
    if not is_valid_id(order_id):
        return _error("invalid_order_id")

    order_id = clean_id(order_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT o.order_status,
               o.order_purchase_timestamp,
               o.order_approved_at,
               o.order_delivered_carrier_date,
               o.order_delivered_customer_date,
               o.order_estimated_delivery_date,
               c.customer_city,
               c.customer_state
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return _error("order_not_found")

    return {
        "order_id": order_id,
        "status": row["order_status"],
        "purchase_date": row["order_purchase_timestamp"],
        "approved_at": row["order_approved_at"],
        "shipped_to_carrier_date": row["order_delivered_carrier_date"],
        "delivered_date": row["order_delivered_customer_date"],
        "estimated_delivery_date": row["order_estimated_delivery_date"],
        "destination_city": row["customer_city"],
        "destination_state": row["customer_state"],
    }


# --------------------------------------------------------------------------
# 5. Product details
# --------------------------------------------------------------------------
def get_product_details(product_id: str):
    if not is_valid_id(product_id):
        return _error("invalid_product_id")

    product_id = clean_id(product_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, product_weight_g
        FROM products
        WHERE product_id = ?
        """,
        (product_id,),
    )
    product_row = cursor.fetchone()

    if product_row is None:
        conn.close()
        return _error("product_not_found")

    cursor.execute(
        """
        SELECT COUNT(*) AS times_ordered,
               MIN(price) AS min_price,
               MAX(price) AS max_price,
               AVG(price) AS avg_price
        FROM order_items
        WHERE product_id = ?
        """,
        (product_id,),
    )
    price_row = cursor.fetchone()
    conn.close()

    result = {
        "product_id": product_id,
        "category": product_row["category"],
        "weight_g": product_row["product_weight_g"],
        "times_ordered": price_row["times_ordered"] or 0,
    }

    if price_row["times_ordered"]:
        result["min_price"] = round(price_row["min_price"], 2)
        result["max_price"] = round(price_row["max_price"], 2)
        result["avg_price"] = round(price_row["avg_price"], 2)

    return result


# --------------------------------------------------------------------------
# 6. Product search by category
# --------------------------------------------------------------------------
def search_products_by_category(category: str, limit: int = 10):
    if not is_valid_category(category):
        return _error("invalid_category")
    if not is_valid_limit(limit):
        limit = 10

    category = clean_category(category)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.product_id,
               p.category,
               AVG(oi.price) AS avg_price
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        WHERE p.category = ?
        GROUP BY p.product_id
        ORDER BY avg_price ASC
        LIMIT ?
        """,
        (category, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return _error("no_products_found")

    return {
        "category": category,
        "products": [
            {
                "product_id": r["product_id"],
                "avg_price": round(r["avg_price"], 2),
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------
# 7. Product search by price range
# --------------------------------------------------------------------------
def search_products_by_price_range(min_price: float, max_price: float, limit: int = 10):
    if not is_valid_price(min_price) or not is_valid_price(max_price):
        return _error("invalid_price_range")
    if float(min_price) > float(max_price):
        return _error("invalid_price_range")
    if not is_valid_limit(limit):
        limit = 10

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.product_id,
               p.category,
               AVG(oi.price) AS avg_price
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        GROUP BY p.product_id
        HAVING avg_price BETWEEN ? AND ?
        ORDER BY avg_price ASC
        LIMIT ?
        """,
        (float(min_price), float(max_price), limit),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return _error("no_products_found")

    return {
        "min_price": float(min_price),
        "max_price": float(max_price),
        "products": [
            {
                "product_id": r["product_id"],
                "category": r["category"],
                "avg_price": round(r["avg_price"], 2),
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------
# 8. Customer's orders
# --------------------------------------------------------------------------
def get_customer_orders(customer_id: str, limit: int = 10):
    if not is_valid_id(customer_id):
        return _error("invalid_customer_id")
    if not is_valid_limit(limit):
        limit = 10

    customer_id = clean_id(customer_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT order_id, order_status, order_purchase_timestamp
        FROM orders
        WHERE customer_id = ?
        ORDER BY order_purchase_timestamp DESC
        LIMIT ?
        """,
        (customer_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return _error("customer_not_found_or_no_orders")

    return {
        "customer_id": customer_id,
        "orders": [
            {
                "order_id": r["order_id"],
                "status": r["order_status"],
                "purchase_date": r["order_purchase_timestamp"],
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------
# 9. Order / customer lookup (minimal, non-identifying customer info only -
#    Olist has no names/emails/phone numbers, so this never leaks PII)
# --------------------------------------------------------------------------
def lookup_order_customer(order_id: str):
    if not is_valid_id(order_id):
        return _error("invalid_order_id")

    order_id = clean_id(order_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT o.customer_id,
               c.customer_city,
               c.customer_state
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return _error("order_not_found")

    return {
        "order_id": order_id,
        "customer_id": row["customer_id"],
        "customer_city": row["customer_city"],
        "customer_state": row["customer_state"],
    }


# --------------------------------------------------------------------------
# Tool registry: intent name -> Python function
# The LLM only ever returns one of these names + matching parameters.
# --------------------------------------------------------------------------
TOOL_REGISTRY = {
    "get_order_status": get_order_status,
    "get_order_items": get_order_items,
    "get_order_total": get_order_total,
    "get_delivery_details": get_delivery_details,
    "get_product_details": get_product_details,
    "search_products_by_category": search_products_by_category,
    "search_products_by_price_range": search_products_by_price_range,
    "get_customer_orders": get_customer_orders,
    "lookup_order_customer": lookup_order_customer,
}


# --------------------------------------------------------------------------
# JSON-schema tool definitions, in the OpenAI/Groq function-calling format.
# The LLM sees ONLY these schemas - never the SQL itself.
# --------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the current status and key dates of a single order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "32-character order ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_items",
            "description": "List the products, categories and prices inside a single order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "32-character order ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_total",
            "description": "Get the total amount paid (items + freight) for a single order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "32-character order ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_details",
            "description": "Get shipping/delivery dates and destination city/state for an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "32-character order ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get category, weight and price stats for a single product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "32-character product ID"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products_by_category",
            "description": "Find products belonging to a given category, cheapest first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "e.g. 'electronics', 'toys', 'furniture_decor'"},
                    "limit": {"type": "integer", "description": "Max results, default 10"},
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products_by_price_range",
            "description": "Find products whose average price falls within a min/max range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_price": {"type": "number"},
                    "max_price": {"type": "number"},
                    "limit": {"type": "integer", "description": "Max results, default 10"},
                },
                "required": ["min_price", "max_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "List recent orders placed by a given customer ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "32-character customer ID"},
                    "limit": {"type": "integer", "description": "Max results, default 10"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order_customer",
            "description": "Given an order ID, find which customer (ID/city/state) it belongs to.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "32-character order ID"},
                },
                "required": ["order_id"],
            },
        },
    },
]
