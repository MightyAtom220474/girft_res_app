import sqlite3
from datetime import datetime
import os
import shutil

BACKUP_DIR = r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Database Backups"
DB_PATH = r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Capacity Planner\girft_res_app\.streamlit\girft_capacity_planner.db"



def backup_db():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")

    shutil.copy2(DB_PATH, backup_path)

    return backup_path

def update_latest(backup_path):
    latest_path = os.path.join(BACKUP_DIR, "latest.db")
    shutil.copy2(backup_path, latest_path)
    print(f"✅ Updated latest.db")


def cleanup_backups(folder, keep=20):
    print("Running cleanup...")

    files = sorted([f for f in os.listdir(folder) if f.endswith(".db")])

    for f in files[:-keep]:
        full_path = os.path.join(folder, f)
        os.remove(full_path)
        print(f"Deleted old backup: {full_path}")


# ✅ MAIN
if __name__ == "__main__":
    backup_path = backup_db()

    if backup_path:
        update_latest(backup_path)
        cleanup_backups(BACKUP_DIR)

    
# shutil.copy2(
#     r"C:\Users\mcdonaldh\OneDrive - Lancashire and South Cumbria NHS Foundation Trust\Documents\NHSE\Database Backups\latest.db",
#     "girft_capacity_planner.db"
# )


