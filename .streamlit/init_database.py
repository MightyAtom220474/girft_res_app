##########################################
# Initialise PostgreSQL DB (ONE-TIME RUN)
# Railway compatible
##########################################

import os
from dotenv import load_dotenv
import psycopg2

# -------------------------------
# Load env
# -------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

# -------------------------------
# Connect
# -------------------------------
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("✅ Connected to PostgreSQL")

# -------------------------------
# PROGRAMME CATEGORIES
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_categories (
    programme_type TEXT,
    programme_group TEXT,
    programme_category TEXT PRIMARY KEY,
    archive_flag INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
)
""")

# -------------------------------
# STAFF LIST
# -------------------------------
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
    must_change_password INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    default_programme TEXT
)
""")

# -------------------------------
# LEAVE CALENDAR
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_calendar (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    days_leave REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (staff_member, week_commencing),
    FOREIGN KEY (staff_member) REFERENCES staff_list(staff_member)
)
""")

# -------------------------------
# PROGRAMME ACTIVITY
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS programme_activity (
    staff_member TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    programme_category TEXT NOT NULL,
    activity_value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (staff_member, week_commencing, programme_category),
    FOREIGN KEY (staff_member) REFERENCES staff_list(staff_member)
)
""")

# -------------------------------
# ON-SITE CALENDAR
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS on_site_calendar (
    staff_member TEXT NOT NULL,
    programme_category TEXT NOT NULL,
    week_commencing DATE NOT NULL,
    week_number INTEGER NOT NULL,
    on_site_days REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(staff_member, programme_category, week_commencing),
    FOREIGN KEY (staff_member) REFERENCES staff_list(staff_member)
)
""")

# -------------------------------
# Commit + close
# -------------------------------
conn.commit()
cursor.close()
conn.close()

print("✅ Tables created successfully in Railway PostgreSQL")