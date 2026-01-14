##########################################
#   code to initialise SQLite database   #
# only needs to be run once to create db #
#  Creates SQLite database tables and if #
#     available, loads data from CSV     #
##########################################
import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")
PC_CSV_PATH = os.path.join(BASE_DIR, "programme_categories.csv")
SL_CSV_PATH = os.path.join(BASE_DIR, "staff_list.csv")
LC_CSV_PATH = os.path.join(BASE_DIR, "annual_leave_calendar.csv")
PR_CSV_PATH = os.path.join(BASE_DIR, "programme_calendar.csv")
OS_CSV_PATH = os.path.join(BASE_DIR, "on_site_calendar.csv")
LD_CSV_PATH = os.path.join(BASE_DIR, "legacy_activity_weekly_normalised.csv") # legacy programme data

for path in [DB_PATH, PC_CSV_PATH, SL_CSV_PATH, LC_CSV_PATH, PR_CSV_PATH, OS_CSV_PATH]:
    if not os.path.exists(path):
        print(f"Warning: {path} does not exist!")
# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
DROP TABLE IF EXISTS programme_categories; 
""")
conn.commit()
cursor.execute("""
DROP TABLE IF EXISTS staff_list; 
""")
conn.commit()               
cursor.execute("""
DROP TABLE IF EXISTS programme_activity; 
""")
conn.commit()
cursor.execute("""
DROP TABLE IF EXISTS leave_calendar;
""")
conn.commit()
cursor.execute("""
DROP TABLE IF EXISTS on_site_calendar;
""")
conn.commit()

##### Programme Categories #####

# Create programme_categories table
cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_categories (
    programme_type TEXT,
    programme_group TEXT,
    programme_categories TEXT PRIMARY KEY,
    archive_flag INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
)
""")

conn.commit()

# if there is already a CSV file, load it

if os.path.exists(PC_CSV_PATH):
    print("CSV found – importing programme_categories data")

    # Load CSV
    df = pd.read_csv(PC_CSV_PATH)

    # Insert data
    df.to_sql("programme_categories", conn, if_exists="append", index=False)

    #conn.close()

# otherwise just advise that table has been created
else:
    print("CSV not found – programme_categories table created only")

##### Staff List #####

# Create staff_list table
cursor.execute("""
CREATE TABLE IF NOT EXISTS staff_list (
    staff_member TEXT PRIMARY KEY,
    job_role TEXT,
    hours_pw REAL,
    leave_allowance_days INTEGER,
    is_deployable INTEGER,
    deploy_ratio REAL,
    archive_flag INTEGER DEFAULT 0,
    username TEXT,
    password TEXT NOT NULL,
    access_level TEXT NOT NULL,
    must_change_password INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NULL
)
""")

conn.commit()

# if there is already a CSV file, load it

if os.path.exists(SL_CSV_PATH):
    print("CSV found – importing staff_list data")

    # Load CSV
    df = pd.read_csv(SL_CSV_PATH)

    # Convert boolean column to integer for SQLite
    df["must_change_password"] = df["must_change_password"].astype(int)

    # Insert data
    df.to_sql("staff_list", conn, if_exists="append", index=False)

    #conn.close()

# otherwise just advise that table has been created
else:
    print("CSV not found – staff_list table created only")

##### Annual Leave Calendar #####
cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_calendar (
    staff_member TEXT NOT NULL,
    week_commencing TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    days_leave INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    PRIMARY KEY (staff_member, week_commencing) 
)
""")

conn.commit()

if os.path.exists(LC_CSV_PATH):
    print("CSV found – importing leave_calendar data")

    df = pd.read_csv(LC_CSV_PATH)

    df.to_sql(
        "leave_calendar",
        conn,
        if_exists="append",
        index=False
    )

    #conn.close()

else:
    print("CSV not found – leave_calendar table created only")

##### Planner Calendar #####


# List of programme activity columns in your CSV
programme_columns = [
    "Action Cards and other resource development",
    "Coaching (not linked to Intensive Support)",
    "Community CAMHS",
    "Core Fidelity and CRHT work",
    "Foundations For Better MH Services",
    "Further Faster",
    "General Admin Tasks",
    "Inpatient Men-SAT",
    "MHED Policy and Clinical Collaboration",
    "Mental Health Rehabilitation",
    "Miscellaneous Consultation, Adv & Support",
    "NHFT",
    "NHS Confed",
    "Neurodivergent Services",
    "St. Andrews",
    "Test",
    "UEC MH Priority Sites",
    "UEC Men-SAT"
]

# Load CSV
df = pd.read_csv(PR_CSV_PATH)

# Normalize: wide → long
long_df = df.melt(
    id_vars=["staff_member", "week_commencing", "week_number"],  # keep these as is
    value_vars=programme_columns,  # melt these into rows
    var_name="programme_category",
    value_name="activity_value"
)

# Keep only rows with meaningful activity
#long_df = long_df[long_df["activity_value"].fillna(0) > 0]

# SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_activity (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    programme_category TEXT NOT NULL,
    activity_value REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    PRIMARY KEY (staff_member, week_commencing, programme_category)
)
""")

conn.commit()

if os.path.exists(PR_CSV_PATH):

    # load normalised data into table
    long_df.to_sql(
        "programme_activity",
        conn,
        if_exists="append",
        index=False
    )

    #conn.close()

else:
    print("CSV not found – programme_activity table created only")

##### load in legacy data if supplied #####

legacy_df = pd.read_csv(LD_CSV_PATH)

print(legacy_df.columns)
legacy_df.head()

if os.path.exists(LD_CSV_PATH):

    # load normalised data into table
    legacy_df.to_sql(
        "programme_activity",
        conn,
        if_exists="append",
        index=False
    )

    #conn.close()

else:
    print("CSV for legacy data not found – programme_activity table created only")

##### On-Site Calendar #####
cursor.execute("""
CREATE TABLE IF NOT EXISTS on_site_calendar (
    staff_member TEXT NOT NULL,
    week_commencing TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    on_site_days INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT  
)
""")

conn.commit()

if os.path.exists(OS_CSV_PATH):
    print("CSV found – importing on_site_calendar data")

    df = pd.read_csv(OS_CSV_PATH)

    df.to_sql(
        "on_site_calendar",
        conn,
        if_exists="append",
        index=False
    )



else:
    print("CSV not found – on_site_calendar table created only")

tables = [
    "staff_list",
    "programme_categories",
    "programme_activity",
    "leave_calendar",
    "on_site_calendar"
]

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    count = cursor.fetchone()[0]
    print(f"{table}: {count} rows")

conn.close()





