import pandas as pd
import sqlite3
from pathlib import Path

# -----------------------------
# 1. File paths
# -----------------------------

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "ecommerce.db"

# -----------------------------
# 2. Load CSV files
# -----------------------------

print("Loading datasets...")

orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
translation = pd.read_csv(
    DATA_DIR / "product_category_name_translation.csv"
)

print("Datasets loaded successfully!")

# -----------------------------
# 3. Select useful columns
# -----------------------------

orders = orders[
    [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
]

order_items = order_items[
    [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ]
]

products = products[
    [
        "product_id",
        "product_category_name",
        "product_weight_g",
    ]
]

customers = customers[
    [
        "customer_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
    ]
]

translation = translation[
    [
        "product_category_name",
        "product_category_name_english",
    ]
]

# -----------------------------
# 4. Translate product categories
# -----------------------------

products = products.merge(
    translation,
    on="product_category_name",
    how="left"
)

products = products.drop(columns=["product_category_name"])

products = products.rename(
    columns={
        "product_category_name_english": "category"
    }
)

# -----------------------------
# 5. Create SQLite database
# -----------------------------

print("Creating SQLite database...")

conn = sqlite3.connect(DB_PATH)

orders.to_sql(
    "orders",
    conn,
    if_exists="replace",
    index=False
)

order_items.to_sql(
    "order_items",
    conn,
    if_exists="replace",
    index=False
)

products.to_sql(
    "products",
    conn,
    if_exists="replace",
    index=False
)

customers.to_sql(
    "customers",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("\nDatabase created successfully!")
print(f"Location: {DB_PATH}")

print("\nRows:")
print("Orders:", len(orders))
print("Order items:", len(order_items))
print("Products:", len(products))
print("Customers:", len(customers))