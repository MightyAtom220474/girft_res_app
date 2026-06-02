##########################################################################
# Run this ONCE to reset all user passwords safely (PostgreSQL version)
##########################################################################

from werkzeug.security import generate_password_hash
from db import execute, query_df

# ============================================
# 🔐 CONFIG
# ============================================
TEMP_PASSWORD = "Temporary123!"  # change if needed

# ============================================
# ✅ GET ALL USERS
# ============================================
users_df = query_df("""
    SELECT username
    FROM staff_list
    WHERE username IS NOT NULL
""")

if users_df.empty:
    print("⚠️ No users found with usernames")
    exit()

print(f"🔍 Found {len(users_df)} users")

# ============================================
# 🔄 RESET PASSWORDS (SECURE WAY)
# ============================================
for username in users_df["username"]:

    # ✅ Generate unique salted hash per user
    hashed_pw = generate_password_hash(TEMP_PASSWORD)

    # ✅ Update user
    execute("""
        UPDATE staff_list
        SET password = %s,
            must_change_password = 1
        WHERE username = %s
    """, (hashed_pw, username))

print("✅ All passwords reset with unique hashed values")

# ============================================
# 🔍 DEBUG CHECK (optional)
# ============================================
sample_user = users_df["username"].iloc[0]

result = query_df("""
    SELECT staff_member, username, must_change_password
    FROM staff_list
    WHERE username = %s
""", (sample_user,))

print("🔎 Sample user check:")
print(result)