from werkzeug.security import generate_password_hash
import planner_functions as pf
import pandas as pd

##############################################################################
# Reset all passwords
##############################################################################

TEMP_PASSWORD = "Temporary123!"

staff_df = pf.load_foundry_dataset("staff_list_0")

# Generate a unique salted hash for each user
staff_df["password"] = [
    generate_password_hash(TEMP_PASSWORD)
    for _ in range(len(staff_df))
]

staff_df["must_change_password"] = 1
staff_df["updated_at"] = pd.Timestamp.now()

pf.save_foundry_dataset(
    "staff_list_0",
    staff_df
)

print("✅ All passwords reset")
print("✅ must_change_password set to 1")

# Load latest data
ds.load_or_refresh_all()

# temp_password = "Temporary123!"
# hashed_pw = generate_password_hash(temp_password)

# # Update dataframe
# ds.staff_list["password"] = hashed_pw
# ds.staff_list["must_change_password"] = 1

# # ✅ Write back to database
# with sqlite3.connect(ds.DB_PATH) as conn:
#     ds.staff_list.to_sql("staff_list", conn, if_exists="replace", index=False)

# ##########################################################################
# # reset all passwords back to default
# ##########################################################################

# DB_PATH = "girft_capacity_planner.db"

# #temp_password = "Temporary123!"

# with sqlite3.connect(DB_PATH) as conn:
#     cur = conn.cursor()

#     # Fetch usernames
#     cur.execute("SELECT username FROM staff_list")
#     usernames = [r[0] for r in cur.fetchall()]

#     for u in usernames:
#         cur.execute("""
#             UPDATE staff_list
#             SET password = ?,
#                 must_change_password = 1,
#                 updated_at = CURRENT_TIMESTAMP
#             WHERE username = ?
#         """, (generate_password_hash(temp_password), u))

#     conn.commit()

# print("Done: all passwords reset (unique salted hashes) and must_change_password set to 1.")

##### check password reset

staff_df = pf.load_foundry_dataset("staff_list_0")

print(
    staff_df[
        staff_df["staff_member"] == "Heath McDonald"
    ]
)