from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from db import get_sqlite_conn, get_pg_engine

# import os

# print("HOST:", os.getenv("PGHOST"))
# print("DB:", os.getenv("PGDATABASE"))
# print("USER:", os.getenv("PGUSER"))



sqlite_conn = get_sqlite_conn()
pg_engine = get_pg_engine()

# Get list of tables
tables = pd.read_sql(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
    sqlite_conn
)

print(f"Found tables: {tables['name'].tolist()}")

for table in tables["name"]:
    print(f"\nMigrating: {table}")

    # Read from SQLite
    df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)

    # Basic safety check
    if df.empty:
        print("  → Skipping (empty table)")
        continue

    # Write to Postgres (APPEND mode for safety)
    try:
        df.to_sql(
            table,
            pg_engine,
            if_exists="replace",   # change to "append" if rerunning carefully
            index=False
        )
        print(f"  → Migrated {len(df)} rows")

    except Exception as e:
        print(f"  → ERROR migrating {table}: {e}")

print("\nMigration complete.")