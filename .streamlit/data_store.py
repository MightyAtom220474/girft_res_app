import os
import pandas as pd
import numpy as np
import pandas as pd
from datetime import date
import planner_functions as pf  # Your existing helper functions
import sqlite3
import streamlit as st

# --------------------------
# Global dataframes
# --------------------------
staff_list = None
programme_list = None
programme_categories = None
programme_calendar_df = None
leave_calendar_df = None
onsite_calendar_df = None
staff_leave_merged_df = None
staff_prog_merged_df = None
staff_prog_combined_df = None
staff_prog_pivot_df = None
staff_leave_df = None
programme_names = None

target_util_rate = 85
default_password = 'Temporary123!'

# fix week_commencing dates due to legacy imports
def parse_week_commencing(df, col="week_commencing"):
    """
    Robustly parse a mixed-format week_commencing column into datetime:
    - Handles existing datetimes
    - Handles ISO strings (YYYY-MM-DD)
    - Handles UK dd/mm/yyyy strings
    - Leaves truly bad/blank values as NaT
    """
    if col not in df.columns:
        return df

    s = df[col]

    # Normalise obvious junk to NaN
    s = s.replace(["", " ", "None", None], np.nan)

    # First pass: let pandas infer (handles datetimes + ISO strings)
    parsed = pd.to_datetime(s, errors="coerce")

    # Second pass: for anything still NaT but not blank, try dd/mm/yyyy explicitly
    mask = parsed.isna() & s.notna()
    if mask.any():
        parsed_second = pd.to_datetime(
            s[mask],
            format="%d/%m/%Y",
            errors="coerce"
        )
        parsed.loc[mask] = parsed_second

    df[col] = parsed.dt.normalize()  # strip time to midnight
    return df

def load_or_refresh_all():
    """
    Loads all dataframes from SQLite and performs all downstream merges
    and calculated fields—stored safely in st.session_state.

    Key outputs in st.session_state:
      - staff_list
      - programme_list
      - programme_calendar_df          (normalised: staff/week/programme_category/activity_value)
      - leave_calendar_df
      - onsite_calendar_df
      - staff_names
      - programme_names
      - staff_week_capacity_df         (staff-week level with deploy_ratio applied)
      - staff_prog_pivot_df            (weekly totals incl. total_non_deploy_hours, util_rate)
    """

    import os
    import sqlite3
    import pandas as pd
    import numpy as np
    import streamlit as st

    # ---------------------------
    # Resolve DB path safely
    # ---------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")

    # ---------------------------
    # Helpers
    # ---------------------------
    def parse_week_commencing(df: pd.DataFrame, col: str = "week_commencing") -> pd.DataFrame:
        """
        Robustly parse mixed-format week_commencing into datetime:
        - Handles existing datetimes
        - Handles ISO strings (YYYY-MM-DD)
        - Handles UK dd/mm/yyyy strings
        - Leaves truly bad/blank values as NaT
        """
        if df is None or col not in df.columns:
            return df

        s = df[col].replace(["", " ", "None", None], np.nan)

        parsed = pd.to_datetime(s, errors="coerce")  # ISO + already-datetime
        mask = parsed.isna() & s.notna()
        if mask.any():
            parsed_second = pd.to_datetime(s[mask], format="%d/%m/%Y", errors="coerce")
            parsed.loc[mask] = parsed_second

        df[col] = parsed.dt.normalize()
        return df

    # ---------------------------
    # 1️⃣ Load base tables
    # ---------------------------
    with sqlite3.connect(DB_PATH) as conn:
        st.session_state.staff_list = pd.read_sql(
            "SELECT * FROM staff_list WHERE archive_flag = 0",
            conn
        )

        st.session_state.programme_list = pd.read_sql(
            "SELECT * FROM programme_categories WHERE archive_flag = 0",
            conn
        )

        # Normalised programme activity
        st.session_state.programme_calendar_df = pd.read_sql(
            "SELECT * FROM programme_activity",
            conn
        )

        st.session_state.leave_calendar_df = pd.read_sql(
            "SELECT * FROM leave_calendar",
            conn
        )

        st.session_state.onsite_calendar_df = pd.read_sql(
            "SELECT * FROM on_site_calendar",
            conn
        )

    # ---------------------------
    # 2️⃣ Parse dates
    # ---------------------------
    st.session_state.programme_calendar_df = parse_week_commencing(
        st.session_state.programme_calendar_df, "week_commencing"
    )
    st.session_state.leave_calendar_df = parse_week_commencing(
        st.session_state.leave_calendar_df, "week_commencing"
    )
    st.session_state.onsite_calendar_df = parse_week_commencing(
        st.session_state.onsite_calendar_df, "week_commencing"
    )

    # Ensure week_number exists and is consistent (derive from week_commencing if needed)
    for name in ["programme_calendar_df", "leave_calendar_df", "onsite_calendar_df"]:
        df = st.session_state[name]
        if df is None or df.empty:
            continue

        if "week_commencing" in df.columns:
            # (redundant after parse_week_commencing, but keeps things robust)
            df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce")

            if "week_number" not in df.columns or df["week_number"].isna().any():
                df["week_number"] = df["week_commencing"].dt.isocalendar().week.astype("Int64")

        st.session_state[name] = df

    # ---------------------------
    # 3️⃣ Lookup lists
    # ---------------------------
    st.session_state.staff_names = sorted(
        st.session_state.staff_list["staff_member"].dropna().unique().tolist()
    )

    # Your programme list column is "programme_categories" (per your schema)
    st.session_state.programme_names = sorted(
        st.session_state.programme_list["programme_categories"].dropna().unique().tolist()
    )

    # ---------------------------
    # 4️⃣ Programme totals (ADAPTED for normalised data)
    #    Compute staff-week totals directly (no wide columns / no merge back onto long df needed)
    # ---------------------------
    prog_df = st.session_state.programme_calendar_df.copy()

    # Guard: if programme activity table is empty, create an empty staff-week frame
    if prog_df is None or prog_df.empty:
        prog_staff_week = pd.DataFrame(columns=["staff_member", "week_commencing", "total_prog_hours"])
    else:
        # Only keep the columns we need (in case DB has extras)
        needed = ["staff_member", "week_commencing", "activity_value"]
        for c in needed:
            if c not in prog_df.columns:
                prog_df[c] = np.nan

        prog_staff_week = (
            prog_df
            .groupby(["staff_member", "week_commencing"], as_index=False)
            .agg(total_prog_hours=("activity_value", "sum"))
        )

    # ---------------------------
    # 5️⃣ Leave totals at staff-week level
    # ---------------------------
    leave_df = st.session_state.leave_calendar_df.copy()

    if leave_df is None or leave_df.empty:
        leave_staff_week = pd.DataFrame(columns=["staff_member", "week_commencing", "total_leave_hours"])
    else:
        if "days_leave" not in leave_df.columns:
            leave_df["days_leave"] = 0

        leave_df["leave_hours"] = leave_df["days_leave"].fillna(0) * 7.5

        leave_staff_week = (
            leave_df
            .groupby(["staff_member", "week_commencing"], as_index=False)
            .agg(total_leave_hours=("leave_hours", "sum"))
        )

    # ---------------------------
    # 6️⃣ Build staff-week capacity table (deploy_ratio applied BEFORE pivot)
    # ---------------------------
    staff_base = st.session_state.staff_list[["staff_member", "hours_pw", "deploy_ratio"]].copy()

    # Combine programme + leave at staff-week level
    staff_week = prog_staff_week.merge(
        leave_staff_week,
        on=["staff_member", "week_commencing"],
        how="outer"
    )

    # Join staff attributes
    staff_week = staff_week.merge(
        staff_base,
        on="staff_member",
        how="left"
    )

    # Fill nulls safely
    staff_week["total_prog_hours"] = staff_week["total_prog_hours"].fillna(0.0)
    staff_week["total_leave_hours"] = staff_week["total_leave_hours"].fillna(0.0)

    # If deploy_ratio missing, assume fully deployable (1.0)
    staff_week["deploy_ratio"] = staff_week["deploy_ratio"].fillna(1.0).astype(float)

    # If hours_pw missing, fallback to 37.5
    staff_week["hours_pw"] = staff_week["hours_pw"].fillna(37.5).astype(float)

    # Contracted hours per staff-week
    staff_week["total_contr_hours"] = staff_week["hours_pw"]

    # Available hours after leave (no negatives)
    staff_week["total_avail_hours"] = (
        staff_week["total_contr_hours"] - staff_week["total_leave_hours"]
    ).clip(lower=0)

    # ✅ Non-deployable hours
    staff_week["total_non_deploy_hours"] = (
        staff_week["total_avail_hours"] * (1 - staff_week["deploy_ratio"])
    )

    # ✅ Utilised hours = programme + non-deployable
    staff_week["total_util_hours"] = (
        staff_week["total_prog_hours"] + staff_week["total_non_deploy_hours"]
    )

    # Store staff-week for debugging/other pages if you want it
    st.session_state.staff_week_capacity_df = staff_week

    # ⭐ Neutralise specific staff capacity contribution
    excluded_staff = ["Lizell Smit", "Andy Polychronakis","Heath McDonald"
                      ,"Legacy Data","Gareth Price","Stephen Duncan"
                      ,"Helen Embleton"]

    mask = staff_week["staff_member"].isin(excluded_staff)

    staff_week.loc[mask, [
        "total_leave_hours",
        "total_contr_hours",
        "total_avail_hours"
    ]] = 0.0

    # ---------------------------
    # 7️⃣ Weekly pivot (sum across staff)
    # ---------------------------
    weekly = (
        staff_week
        .groupby("week_commencing", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
            staff_count=("staff_member", "nunique"),
        )
        .sort_values("week_commencing")
        .reset_index(drop=True)
    )

    # ✅ Util rate = (non-deploy + programme) / avail * 100
    weekly["util_rate"] = 0.0
    nonzero = weekly["total_avail_hours"] > 0
    weekly.loc[nonzero, "util_rate"] = (
        (weekly.loc[nonzero, "total_non_deploy_hours"] + weekly.loc[nonzero, "total_prog_hours"])
        / weekly.loc[nonzero, "total_avail_hours"]
        * 100
    )

    weekly["util_target"] = target_util_rate

    # Final store
    st.session_state.staff_prog_pivot_df = weekly

    # ---------------------------
    # 8️⃣ Monthly summary (month taken from week commencing Monday)
    # ---------------------------
    monthly = weekly.copy()

    # Month from the Monday date
    monthly["month"] = monthly["week_commencing"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        monthly
        .groupby("month", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
            staff_count=("staff_count", "mean"),  # average staff in month
        )
        .sort_values("month")
    )

    # Example user-selected start date
    user_input_date = "01-02-2026"
    start_month = pd.to_datetime(user_input_date, dayfirst=True).to_period("M").to_timestamp()

    # Filter out months before start
    monthly = monthly.loc[monthly["month"] >= start_month].sort_values("month")

    # Load and prepare legacy file
    legacy_monthly = pd.read_csv("legacy_capacity_monthly.csv")
    # ✅ Correct parsing: day/month/year format
    legacy_monthly["month"] = pd.to_datetime(
        legacy_monthly["month"],
        dayfirst=True,   # This fixes the issue
        errors="coerce"
    )
    # Normalize to month start
    legacy_monthly["month"] = legacy_monthly["month"].dt.to_period("M").dt.to_timestamp()

    # Combine both
    combined_monthly = pd.concat([legacy_monthly, monthly], ignore_index=True)
    combined_monthly = (
        combined_monthly
        .drop_duplicates(subset=["month"], keep="last")
        .sort_values("month")
        .reset_index(drop=True)
    )
    # Calculate utilisation rate correctly
    combined_monthly["util_rate"] = (
        (combined_monthly["total_non_deploy_hours"] + combined_monthly["total_prog_hours"])
        / combined_monthly["total_avail_hours"]
        * 100
    )
    combined_monthly["util_target"] = target_util_rate
    st.session_state.staff_prog_monthly_df = combined_monthly



# import sqlite3

# DB_PATH = "girft_capacity_planner.db"

# with sqlite3.connect(DB_PATH) as conn:
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT DISTINCT staff_member
#         FROM leave_calendar
#         ORDER BY staff_member
#     """)
#     available_staff = [row[0] for row in cursor.fetchall()]

# print(available_staff)

# with sqlite3.connect(DB_PATH) as conn:
#     cur = conn.cursor()

#     if available_staff:
#         placeholders = ",".join("?" for _ in available_staff)
#         query = f"""
#         DELETE FROM programme_activity
#         WHERE staff_member NOT IN ({placeholders})
#         """
#         cur.execute(query, available_staff)
#     else:
#         cur.execute("DELETE FROM programme_activity")

#     conn.commit()


