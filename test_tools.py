from src.tools import get_order_status, get_order_items


order_id = "53cdb2fc8bc7dce0b6741e2150273451"

print("ORDER STATUS")
print(get_order_status(order_id))

print("\nORDER ITEMS")
print(get_order_items(order_id))