import sqlite3

DB_PATH = "data/ecommerce.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Show all tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table';
""")

tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print("-", table[0])

conn.close()