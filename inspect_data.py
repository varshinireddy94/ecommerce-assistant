import pandas as pd

customers = pd.read_csv("data/olist_customers_dataset.csv")

print("Customer columns:")
print(customers.columns.tolist())

print("\nFirst 5 customers:")
print(customers.head())