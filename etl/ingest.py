"""
ETL script: loads data/sales.csv, cleans it, and pushes it into
the customers, products, and orders tables in Supabase Postgres.

Run this AFTER running database/schema.sql once against your database
(schema.sql creates the empty tables; this script fills them).
"""

import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. Load environment variables
# ---------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Check your .env file.")

engine = create_engine(DATABASE_URL)

# ---------------------------------------------------------
# 2. Load CSV
# ---------------------------------------------------------
print("Loading CSV...")
df = pd.read_csv("data/sales.csv", encoding="latin1")

print(f"Loaded {len(df)} rows.")
print("Columns found:", list(df.columns))

# ---------------------------------------------------------
# 3. Clean column names (snake_case, no spaces)
# ---------------------------------------------------------
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("-", "_")
)

# ---------------------------------------------------------
# 4. Clean data
# ---------------------------------------------------------
before = len(df)
df = df.drop_duplicates()
print(f"Dropped {before - len(df)} duplicate rows.")

df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", dayfirst=False)
df["ship_date"] = pd.to_datetime(df["ship_date"], format="mixed", dayfirst=False)

essential_cols = ["row_id", "order_id", "customer_id", "product_id", "sales"]
before = len(df)
df = df.dropna(subset=essential_cols)
print(f"Dropped {before - len(df)} rows missing essential fields.")

# ---------------------------------------------------------
# 5. Build customers table (deduplicated)
# ---------------------------------------------------------
customers = (
    df[["customer_id", "customer_name", "segment", "country",
        "city", "state", "postal_code", "region"]]
    .drop_duplicates(subset="customer_id")
)

# ---------------------------------------------------------
# 6. Build products table (deduplicated)
# ---------------------------------------------------------
products = (
    df[["product_id", "category", "sub_category", "product_name"]]
    .drop_duplicates(subset="product_id")
)

# ---------------------------------------------------------
# 7. Build orders table (fact table)
# ---------------------------------------------------------
orders = df[["row_id", "order_id", "order_date", "ship_date",
             "ship_mode", "customer_id", "product_id", "sales"]]

# ---------------------------------------------------------
# 8. Push to Supabase
# ---------------------------------------------------------
print("Uploading customers...")
customers.to_sql("customers", engine, if_exists="append", index=False)

print("Uploading products...")
products.to_sql("products", engine, if_exists="append", index=False)

print("Uploading orders...")
orders.to_sql("orders", engine, if_exists="append", index=False)

print("Done. Data loaded into Supabase successfully.")