##########################################################################
# only run this file once when initially setting up the hashed passwords #
##########################################################################

from werkzeug.security import generate_password_hash
import data_store as ds
import sqlite3

DB_PATH = "girft_capacity_planner.db"

temp_password = "Temporary123!"
hashed_pw = generate_password_hash(temp_password)

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()

    cur.execute("""
        UPDATE staff_list
        SET password = ?,
            must_change_password = 1
    """, (hashed_pw,))

    conn.commit()

print("✅ All staff passwords reset and flagged for change")


# Load latest data
ds.load_or_refresh_all()

temp_password = "Temporary123!"
hashed_pw = generate_password_hash(temp_password)

# Update dataframe
ds.staff_list["password"] = hashed_pw
ds.staff_list["must_change_password"] = 1

# ✅ Write back to database
with sqlite3.connect(ds.DB_PATH) as conn:
    ds.staff_list.to_sql("staff_list", conn, if_exists="replace", index=False)

##########################################################################
# reset all passwords back to default
##########################################################################

DB_PATH = "girft_capacity_planner.db"

#temp_password = "Temporary123!"

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()

    # Fetch usernames
    cur.execute("SELECT username FROM staff_list")
    usernames = [r[0] for r in cur.fetchall()]

    for u in usernames:
        cur.execute("""
            UPDATE staff_list
            SET password = ?,
                must_change_password = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
        """, (generate_password_hash(temp_password), u))

    conn.commit()

print("Done: all passwords reset (unique salted hashes) and must_change_password set to 1.")

##### check password reset

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM staff_list where staff_member = 'Heath McDonald' ")
    print(cur.fetchone())  