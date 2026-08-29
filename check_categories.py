import pandas as pd

products = pd.read_csv("data/olist_products_dataset.csv")

categories = sorted(
    products["product_category_name"]
    .dropna()
    .unique()
)

print("Number of categories:", len(categories))

for category in categories:
    print(category)