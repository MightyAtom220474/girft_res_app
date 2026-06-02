import sqlite3, pandas as pd
from data_store import DB_PATH
with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql("SELECT staff_member, week_commencing, on_site_days FROM on_site_calendar WHERE staff_member LIKE '%Conn%' ORDER BY week_commencing DESC", conn)
    print(df.head(50))

# import datetime
# print(datetime.date.today())

import os
print("CWD:", os.getcwd())
print("DB_PATH used here:", os.path.abspath("girft_capacity_planner.db"))