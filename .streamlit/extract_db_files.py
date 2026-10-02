import sqlite3
import pandas as pd

conn = sqlite3.connect("girft_capacity_planner.db")

tables = pd.read_sql("""
SELECT name
FROM sqlite_master
WHERE type='table'
""", conn)

for table in tables["name"]:
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    df.to_csv(f"database_files/{table}.csv", index=False)
    print(f"Created {table}.csv")

conn.close()