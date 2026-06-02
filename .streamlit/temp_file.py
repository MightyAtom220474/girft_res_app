from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_PUBLIC")

print("DATABASE_URL:", DATABASE_URL)

engine = create_engine(DATABASE_URL)

query = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"""

df = pd.read_sql(query, engine)

print("\nTables found:")
print(df)

from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine, text

# --------------------------------------------------
# Load environment
# --------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_PUBLIC")

print("DATABASE_URL:", DATABASE_URL)

engine = create_engine(DATABASE_URL)

# --------------------------------------------------
# 1. Get all tables
# --------------------------------------------------
tables_query = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"""

tables_df = pd.read_sql(tables_query, engine)

print("\n✅ Tables found:")
print(tables_df)


# --------------------------------------------------
# 2. Get row counts for EACH table
# --------------------------------------------------
print("\n✅ Row counts per table:")

table_counts = []



import os
from sqlalchemy import create_engine

DATABASE_URL = (
    f"postgresql://{os.getenv('PGUSER')}:"
    f"{os.getenv('PGPASSWORD')}@"
    f"{os.getenv('PGHOST')}:"
    f"{os.getenv('PGPORT')}/"
    f"{os.getenv('PGDATABASE')}"
)

engine = create_engine(DATABASE_URL)

query = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"""

df = pd.read_sql(query, engine)

print("\nTables found:")
print(df)

from dotenv import load_dotenv
import os

load_dotenv()

print("DATABASE_URL =", os.getenv("DATABASE_URL"))
print("PGHOST =", os.getenv("PGHOST"))
print("PGPORT =", os.getenv("PGPORT"))
print("PGDATABASE =", os.getenv("PGDATABASE"))
print("PGUSER =", os.getenv("PGUSER"))

from dotenv import load_dotenv
load_dotenv()

print("DATABASE_URL =", os.getenv("DATABASE_URL"))
print("DATABASE_PUBLIC_URL =", os.getenv("DATABASE_PUBLIC_URL"))

from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine, text

# --------------------------------------------------
# LOAD ENVIRONMENT
# --------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_PUBLIC")

print("====================================")
print("🔍 DATABASE DEBUG START")
print("====================================\n")

print("✅ DATABASE_URL:")
print(DATABASE_URL if DATABASE_URL else "❌ NOT SET")


# --------------------------------------------------
# CREATE ENGINE
# --------------------------------------------------
try:
    engine = create_engine(DATABASE_URL)
    print("\n✅ Engine created successfully")
except Exception as e:
    print("\n❌ Failed to create engine:", e)
    exit()


# --------------------------------------------------
# TEST CONNECTION
# --------------------------------------------------
try:
    test_df = pd.read_sql("SELECT 1 AS test", engine)
    print("\n✅ Connection test passed:")
    print(test_df)
except Exception as e:
    print("\n❌ Connection test FAILED:", e)
    exit()


# --------------------------------------------------
# CHECK DATABASE + USER
# --------------------------------------------------
try:
    info_df = pd.read_sql(
        "SELECT current_database(), current_user",
        engine
    )
    print("\n✅ Connected to:")
    print(info_df)
except Exception as e:
    print("\n⚠️ Could not fetch DB info:", e)


# --------------------------------------------------
# GET TABLES (Postgres-safe)
# --------------------------------------------------
tables_query = """
SELECT tablename AS table_name
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
"""

try:
    tables_df = pd.read_sql(tables_query, engine)

    print("\n✅ Tables found:")
    print(tables_df)

    print("\nDEBUG table list:")
    print(tables_df["table_name"].tolist())

except Exception as e:
    print("\n❌ Failed to fetch tables:", e)
    exit()


# --------------------------------------------------
# ROW COUNTS FOR EACH TABLE
# --------------------------------------------------
print("\n✅ ROW COUNTS PER TABLE:\n")

if tables_df.empty:
    print("❌ No tables found — likely wrong DB connection")
else:
    for table in tables_df["table_name"]:
        try:
            count_query = text(f'SELECT COUNT(*) AS count FROM "{table}"')
            count_df = pd.read_sql(count_query, engine)

            row_count = int(count_df["count"].iloc[0])
            print(f"{table}: {row_count}")

        except Exception as e:
            print(f"{table}: ERROR -> {e}")


# --------------------------------------------------
# DIRECT staff_list TEST
# --------------------------------------------------
print("\n✅ DIRECT staff_list CHECK:\n")

try:
    staff_total = pd.read_sql(
        'SELECT COUNT(*) AS total FROM "staff_list"',
        engine
    )
    print("Total rows:", int(staff_total["total"].iloc[0]))

    staff_active = pd.read_sql(
        """
        SELECT COUNT(*) AS active
        FROM "staff_list"
        WHERE COALESCE(archive_flag, 0) = 0
        """,
        engine
    )
    print("Active rows:", int(staff_active["active"].iloc[0]))

    sample = pd.read_sql(
        'SELECT * FROM "staff_list" LIMIT 5',
        engine
    )
    print("\nSample rows:")
    print(sample)

except Exception as e:
    print("❌ staff_list query failed:", e)


# --------------------------------------------------
# FINAL CHECK
# --------------------------------------------------
print("\n====================================")
print("🔍 DATABASE DEBUG END")
print("====================================")