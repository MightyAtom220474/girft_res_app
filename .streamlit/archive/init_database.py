import psycopg2
import pandas as pd
import os
from urllib.parse import urlparse

# ========================
# ✅ Connect to PostgreSQL
# ========================
DATABASE_URL = os.getenv("DATABASE_URL_PUBLIC")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("✅ Connected to PostgreSQL")

# ========================
# 📂 CSV paths
# ========================
PC_CSV_PATH = "programme_categories.csv"
SL_CSV_PATH = "staff_list.csv"
LC_CSV_PATH = "annual_leave_calendar.csv"
PR_CSV_PATH = "legacy_activity_weekly_normalised.csv"
OS_CSV_PATH = "on_site_calendar.csv"

# ========================
# 🏗️ CREATE TABLES
# ========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_categories (
    programme_type TEXT,
    programme_group TEXT,
    programme_category TEXT PRIMARY KEY,
    archive_flag INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS staff_list (
    staff_member TEXT PRIMARY KEY,
    job_role TEXT,
    hours_pw REAL,
    leave_allowance_days INTEGER,
    is_deployable INTEGER,
    deploy_ratio REAL,
    archive_flag INTEGER DEFAULT 0,
    username TEXT UNIQUE,
    password TEXT NOT NULL,
    access_level TEXT NOT NULL,
    must_change_password INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_calendar (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    days_leave INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_activity (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    programme_category TEXT NOT NULL,
    activity_value REAL NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS on_site_calendar (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    on_site_days INTEGER DEFAULT 0
)
""")

conn.commit()

print("✅ Tables created")

# ========================
# 📥 LOAD CSV FUNCTION
# ========================
def load_csv(table_name, file_path, preprocess=None):
    if not os.path.exists(file_path):
        print(f"⚠️ {file_path} not found")
        return

    print(f"📥 Loading {table_name}")

    df = pd.read_csv(file_path)

    if preprocess:
        df = preprocess(df)

    # Clear table first (keeps schema intact)
    cursor.execute(f"DELETE FROM {table_name}")

    # Insert data row by row
    cols = list(df.columns)
    col_str = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    insert_sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"

    for row in df.itertuples(index=False, name=None):
        cursor.execute(insert_sql, row)

    conn.commit()
    print(f"✅ {table_name} loaded")


# ========================
# 🧹 PREPROCESS FUNCTIONS
# ========================
def preprocess_staff(df):
    if "must_change_password" in df.columns:
        df["must_change_password"] = df["must_change_password"].astype(int)
    return df


# ========================
# 🚀 LOAD DATA
# ========================
load_csv("programme_categories", PC_CSV_PATH)
load_csv("staff_list", SL_CSV_PATH, preprocess=preprocess_staff)
load_csv("leave_calendar", LC_CSV_PATH)
load_csv("programme_activity", PR_CSV_PATH)
load_csv("on_site_calendar", OS_CSV_PATH)

# ========================
# 🔒 CLOSE
# ========================
cursor.close()
conn.close()

print("🎉 Database setup complete")