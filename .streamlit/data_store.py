import os
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
            "SELECT * FROM staff_list WHERE archive_flag = 0", conn
        )

        st.session_state.programme_list = pd.read_sql(
            "SELECT * FROM programme_categories WHERE archive_flag = 0", conn
        )

        st.session_state.programme_calendar_df = pd.read_sql(
            "SELECT * FROM programme_activity", conn
        )

        st.session_state.leave_calendar_df = pd.read_sql(
            "SELECT * FROM leave_calendar", conn
        )

        st.session_state.onsite_calendar_df = pd.read_sql(
            "SELECT * FROM on_site_calendar", conn
        )

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
        .groupby(["staff_member", "week_number"], as_index=False)
        .agg(total_prog_hours=("activity_value", "sum"))
    )

    st.session_state.programme_calendar_df = (
        st.session_state.programme_calendar_df
        .merge(programme_totals, on=["staff_member", "week_number"], how="left")
    )

    st.session_state.programme_calendar_df["total_prog_hours"] = (
        st.session_state.programme_calendar_df["total_prog_hours"].fillna(0)
    )

    # ---------------------------
    # 4️⃣ Leave calculations
    # ---------------------------
    st.session_state.leave_calendar_df["leave_hours"] = (
        st.session_state.leave_calendar_df["days_leave"] * 7.5
    )

    st.session_state.staff_leave_merged_df = (
        st.session_state.leave_calendar_df
        .merge(st.session_state.staff_list, on="staff_member", how="left")
    )

    st.session_state.staff_leave_merged_df["avail_hours"] = (
        st.session_state.staff_leave_merged_df["hours_pw"]
        - st.session_state.staff_leave_merged_df["leave_hours"]
    )

    # ---------------------------
    # 5️⃣ Programme + staff merge
    # ---------------------------
    st.session_state.staff_prog_merged_df = (
        st.session_state.programme_calendar_df
        .merge(st.session_state.staff_list, on="staff_member", how="left")
    )

    st.session_state.staff_leave_df = (
        st.session_state.leave_calendar_df
        .groupby(["staff_member", "week_number"], as_index=False)
        .agg(total_leave_hours=("leave_hours", "sum"))
    )

    st.session_state.staff_prog_combined_df = (
        st.session_state.staff_prog_merged_df
        .merge(
            st.session_state.staff_leave_df,
            on=["staff_member", "week_number"],
            how="left",
        )
    )

    st.session_state.staff_prog_combined_df["total_leave_hours"] = (
        st.session_state.staff_prog_combined_df["total_leave_hours"].fillna(0)
    )

    # ---------------------------
    # 6️⃣ Derived metrics
    # ---------------------------
    df = st.session_state.staff_prog_combined_df

    df["total_contr_hours"] = df["hours_pw"]

    df["total_avail_hours"] = (
        df["hours_pw"] - df["total_leave_hours"]
    )

    df["total_non_deploy_hours"] = (
        df["total_avail_hours"] * (1 - df["deploy_ratio"])
    )

    df["total_util_hours"] = (
        df["total_prog_hours"] + df["total_non_deploy_hours"]
    )

    st.session_state.staff_prog_combined_df = df

    # ---------------------------
    # 7️⃣ Weekly pivot
    # ---------------------------
    st.session_state.staff_prog_pivot_df = (
        df.groupby("week_number", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
        )
    )

    st.session_state.staff_prog_pivot_df["util_rate"] = (
        st.session_state.staff_prog_pivot_df["total_util_hours"]
        / st.session_state.staff_prog_pivot_df["total_avail_hours"]
    ) * 100

    st.session_state.staff_prog_pivot_df["util_target"] = target_util_rate
