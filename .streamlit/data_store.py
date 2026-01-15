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
    """

    # ---------------------------
    # Resolve DB path safely
    # ---------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")

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

        st.session_state.programme_calendar_df = parse_week_commencing(
        st.session_state.programme_calendar_df,
        "week_commencing"
            )
        st.session_state.leave_calendar_df = parse_week_commencing(
            st.session_state.leave_calendar_df,
            "week_commencing"
        )
        st.session_state.onsite_calendar_df = parse_week_commencing(
            st.session_state.onsite_calendar_df,
            "week_commencing"
        )


    # 🔹 Convert week_commencing strings → datetime with UK dd/mm/yyyy
    for name in ["programme_calendar_df", "leave_calendar_df", "onsite_calendar_df"]:
        df = st.session_state[name]
        if "week_commencing" in df.columns:
            df["week_commencing"] = pd.to_datetime(
                df["week_commencing"],
                errors="coerce",
                dayfirst=True,   # 👈 THIS is what your dd/mm/yyyy needs
            )
            st.session_state[name] = df


    # # 🔹 Normalise week_commencing in every calendar table
    # st.session_state.programme_calendar_df = coerce_week_commencing(
    #     st.session_state.programme_calendar_df, "week_commencing"
    # )
    # st.session_state.leave_calendar_df = coerce_week_commencing(
    #     st.session_state.leave_calendar_df, "week_commencing"
    # )
    # st.session_state.onsite_calendar_df = coerce_week_commencing(
    #     st.session_state.onsite_calendar_df, "week_commencing"
    # )

    # # 🔹 Normalise week_commencing in every calendar table
    # st.session_state.programme_calendar_df = coerce_week_commencing(
    #     st.session_state.programme_calendar_df, "week_commencing"
    # )
    # st.session_state.leave_calendar_df = coerce_week_commencing(
    #     st.session_state.leave_calendar_df, "week_commencing"
    # )
    # st.session_state.onsite_calendar_df = coerce_week_commencing(
    #     st.session_state.onsite_calendar_df, "week_commencing"
    # )

    # ---------------------------
    # 2️⃣ Convenience lists
    # ---------------------------
    st.session_state.staff_names = sorted(
        st.session_state.staff_list["staff_member"].dropna().unique().tolist()
    )

    st.session_state.programme_names = sorted(
        st.session_state.programme_list["programme_categories"].dropna().unique().tolist()
    )

    # ---------------------------
    # 3️⃣ Programme totals (NORMALISED)
    # ---------------------------
    programme_totals = (
        st.session_state.programme_calendar_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(total_prog_hours=("activity_value", "sum"))
    )

    st.session_state.programme_calendar_df = (
        st.session_state.programme_calendar_df
        .merge(programme_totals, on=["staff_member", "week_commencing"], how="left")
    )

    st.session_state.programme_calendar_df["total_prog_hours"] = (
        st.session_state.programme_calendar_df["total_prog_hours"].fillna(0)
    )

    # # ---------------------------
    # # 4️⃣ Leave calculations
    # # ---------------------------
    # st.session_state.leave_calendar_df["leave_hours"] = (
    #     st.session_state.leave_calendar_df["days_leave"] * 7.5
    # )

    # st.session_state.staff_leave_merged_df = (
    #     st.session_state.leave_calendar_df
    #     .merge(st.session_state.staff_list, on="staff_member", how="left")
    # )

    # st.session_state.staff_leave_merged_df["avail_hours"] = (
    #     st.session_state.staff_leave_merged_df["hours_pw"]
    #     - st.session_state.staff_leave_merged_df["leave_hours"]
    # )

    # # ---------------------------
    # # 5️⃣ Programme + staff merge
    # # ---------------------------
    # st.session_state.staff_prog_merged_df = (
    #     st.session_state.programme_calendar_df
    #     .merge(st.session_state.staff_list, on="staff_member", how="left")
    # )

    # st.session_state.staff_leave_df = (
    #     st.session_state.leave_calendar_df
    #     .groupby(["staff_member", "week_commencing"], as_index=False)
    #     .agg(total_leave_hours=("leave_hours", "sum"))
    # )

    # st.session_state.staff_prog_combined_df = (
    #     st.session_state.staff_prog_merged_df
    #     .merge(
    #         st.session_state.staff_leave_df,
    #         on=["staff_member", "week_commencing"],
    #         how="left",
    #     )
    # )

    # st.session_state.staff_prog_combined_df["total_leave_hours"] = (
    #     st.session_state.staff_prog_combined_df["total_leave_hours"].fillna(0)
    # )

    # # ---------------------------
    # # 6️⃣ Derived metrics
    # # ---------------------------
    # df = st.session_state.staff_prog_combined_df

    # df["total_contr_hours"] = df["hours_pw"]

    # df["total_avail_hours"] = (
    #     df["hours_pw"] - df["total_leave_hours"]
    # )

    # df["total_non_deploy_hours"] = (
    #     df["total_avail_hours"] * (1 - df["deploy_ratio"])
    # )

    # df["total_util_hours"] = (
    #     df["total_prog_hours"] + df["total_non_deploy_hours"]
    # )

    # st.session_state.staff_prog_combined_df = df

    # # ---------------------------
    # # 7️⃣ Weekly pivot
    # # ---------------------------
    # st.session_state.staff_prog_pivot_df = (
    #     df.groupby("week_commencing", as_index=False)
    #     .agg(
    #         total_leave_hours=("total_leave_hours", "sum"),
    #         total_contr_hours=("total_contr_hours", "sum"),
    #         total_avail_hours=("total_avail_hours", "sum"),
    #         total_prog_hours=("total_prog_hours", "sum"),
    #         total_non_deploy_hours=("total_non_deploy_hours", "sum"),
    #         total_util_hours=("total_util_hours", "sum"),
    #     )
    # )

    # st.session_state.staff_prog_pivot_df["util_rate"] = (
    #     st.session_state.staff_prog_pivot_df["total_util_hours"]
    #     / st.session_state.staff_prog_pivot_df["total_avail_hours"]
    # ) * 100

    # st.session_state.staff_prog_pivot_df["util_target"] = target_util_rate

    # # ---------------------------
    # # 4️⃣ Leave: weekly totals from leave_calendar_df
    # # ---------------------------
    # # days_leave already per staff/week; convert to hours
    # st.session_state.leave_calendar_df["leave_hours"] = (
    #     st.session_state.leave_calendar_df["days_leave"] * 7.5
    # )

    # leave_weekly = (
    #     st.session_state.leave_calendar_df
    #     .groupby("week_commencing", as_index=False)
    #     .agg(
    #         total_leave_hours=("leave_hours", "sum"),
    #         staff_count=("staff_member", "nunique")   # how many staff have leave recorded
    #     )
    # )

    # # ---------------------------
    # # 5️⃣ Programme: weekly totals from programme_calendar_df
    # # ---------------------------
    # prog_weekly = (
    #     st.session_state.programme_calendar_df
    #     .groupby("week_commencing", as_index=False)
    #     .agg(
    #         total_prog_hours=("activity_value", "sum")
    #     )
    # )

    # # ---------------------------
    # # 6️⃣ Combine at week level & derive metrics
    # # ---------------------------
    # weekly = prog_weekly.merge(
    #     leave_weekly,
    #     on="week_commencing",
    #     how="outer"     # include weeks that have only prog or only leave
    # )

    # weekly["total_prog_hours"] = weekly["total_prog_hours"].fillna(0)
    # weekly["total_leave_hours"] = weekly["total_leave_hours"].fillna(0)
    # weekly["staff_count"] = weekly["staff_count"].fillna(0)

    # # Assume 37.5 hours per staff per week
    # weekly["total_contr_hours"] = weekly["staff_count"] * 37.5

    # # Capacity after leave
    # weekly["total_avail_hours"] = (
    #     weekly["total_contr_hours"] - weekly["total_leave_hours"]
    # )

    # # If you want to ignore non-deployable overhead for this legacy-style calc:
    # weekly["total_non_deploy_hours"] = 0.0

    # weekly["total_util_hours"] = (
    #     weekly["total_prog_hours"] + weekly["total_non_deploy_hours"]
    # )

    # # Avoid divide-by-zero
    # weekly["util_rate"] = 0.0
    # nonzero_mask = weekly["total_avail_hours"] > 0
    # weekly.loc[nonzero_mask, "util_rate"] = (
    #     weekly.loc[nonzero_mask, "total_util_hours"]
    #     / weekly.loc[nonzero_mask, "total_avail_hours"]
    #     * 100
    # )

    # weekly["util_target"] = target_util_rate

    # # Store as your weekly pivot
    # st.session_state.staff_prog_pivot_df = weekly

    # ---------------------------
    # 4️⃣ Leave: weekly totals from leave_calendar_df
    # ---------------------------
    # days_leave already per staff/week; convert to hours
    st.session_state.leave_calendar_df["leave_hours"] = (
        st.session_state.leave_calendar_df["days_leave"] * 7.5
    )

    # aggregate the total leave hours by week_commencing and get a count of the staff that week
    leave_weekly = (
        st.session_state.leave_calendar_df
        .groupby("week_commencing", as_index=False)
        .agg(
            total_leave_hours=("leave_hours", "sum"),
            staff_count=("staff_member", "nunique")   # how many staff have leave recorded
        )
    )

    # ---------------------------
    # 5️⃣ Programme: weekly totals from programme_calendar_df
    # ---------------------------
    # aggregate the programme activity by week_commencing ang et total of prog hours
    prog_weekly = (
        st.session_state.programme_calendar_df
        .groupby("week_commencing", as_index=False)
        .agg(
            total_prog_hours=("activity_value", "sum")
        )
    )

    # ---------------------------
    # 6️⃣ Combine at week level & derive metrics
    # ---------------------------
    weekly = prog_weekly.merge(
        leave_weekly,
        on="week_commencing",
        how="outer"     # include weeks that have only prog or only leave
    )

    weekly["total_prog_hours"] = weekly["total_prog_hours"].fillna(0)
    weekly["total_leave_hours"] = weekly["total_leave_hours"].fillna(0)
    weekly["staff_count"] = weekly["staff_count"].fillna(0)

    # Assume 37.5 hours per staff per week
    weekly["total_contr_hours"] = weekly["staff_count"] * 37.5

    # Capacity after leave
    weekly["total_avail_hours"] = (
        weekly["total_contr_hours"] - weekly["total_leave_hours"]
    )

    # Ignore deployable overhead for legacy-style calc
    weekly["total_non_deploy_hours"] = 0.0

    weekly["total_util_hours"] = (
        weekly["total_prog_hours"] + weekly["total_non_deploy_hours"]
    )

    # Avoid divide-by-zero
    weekly["util_rate"] = 0.0
    nonzero_mask = weekly["total_avail_hours"] > 0
    weekly.loc[nonzero_mask, "util_rate"] = (
        weekly.loc[nonzero_mask, "total_util_hours"]
        / weekly.loc[nonzero_mask, "total_avail_hours"]
        * 100
    )

    weekly["util_target"] = target_util_rate

    # Store as your weekly pivot
    st.session_state.staff_prog_pivot_df = weekly

# import sqlite3

# DB_PATH = "girft_capacity_planner.db"

# with sqlite3.connect(DB_PATH) as conn:
#     cur = conn.cursor()
#     # Delete all existing legacy rows
#     cur.execute("DELETE FROM programme_activity WHERE staff_member = 'Legacy Data'")
#     conn.commit()


    

