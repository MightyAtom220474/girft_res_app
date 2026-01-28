##########################################################################
# only run this file once when initially setting up the hashed passwords #
##########################################################################

from werkzeug.security import generate_password_hash
import data_store as ds
import sqlite3

ds.load_or_refresh_all()
temp_password = "Temporary123!"
ds.staff_list["password"] = ds.staff_list["username"].apply(
    lambda u: generate_password_hash(temp_password)
)
ds.staff_list["must_change_password"] = True
ds.staff_list.to_csv("staff_list.csv", index=False)

##########################################################################
# reset all passwords back to default
##########################################################################

DB_PATH = "girft_capacity_planner.db"

temp_password = "Temporary123!"

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
    cur.execute("SELECT * FROM staff_list")
    print(cur.fetchone())  