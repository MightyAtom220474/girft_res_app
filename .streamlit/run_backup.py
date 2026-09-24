import sqlite3
import os
import shutil
from datetime import datetime
import sys

# ✅ LOGGING
log_file = open(r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Database Backups\backup_log.txt", "a")
sys.stdout = log_file
sys.stderr = log_file

DB_PATH = r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Capacity Planner\girft_res_app\.streamlit\girft_capacity_planner.db"

BACKUP_DIR = r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Database Backups"

#LOG_FILE = r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Database Backups\backup_log.txt"

print("Starting backup...")

os.makedirs(BACKUP_DIR, exist_ok=True)

backup_path = os.path.join(
    BACKUP_DIR,
    f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

print(f"Backing up to: {backup_path}")


# ✅ SAFETY CHECK
if not os.path.exists(DB_PATH):
    print(f"❌ DB not found: {DB_PATH}")
else:
    try:
        shutil.copy2(DB_PATH, backup_path)
        print("✅ Backup complete")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

print("---- Script finished ----\n")
log_file.close()


