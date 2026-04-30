#import os
import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta
import sqlite3
import streamlit as st
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")

# --------------------------
# Global settings
# --------------------------
target_util_rate = 85
default_password = generate_password_hash("Temporary123!")

# --------------------------
# Helpers
# --------------------------
def parse_week_commencing(df, col="week_commencing"):
    if col not in df.columns:
        return df

    s = df[col].replace(["", " ", "None", None], np.nan)
    parsed = pd.to_datetime(s, errors="coerce")

    mask = parsed.isna() & s.notna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(
            s[mask], format="%d/%m/%Y", dayfirst=True, errors="coerce"
        )

    df[col] = parsed.dt.normalize()
    return df


def handle_trigger_reload():
    trigger = st.session_state.get("trigger_reload")
    if trigger == "leave":
        refresh_leave_calendar()
    elif trigger == "onsite":
        refresh_onsite_calendar()
    elif trigger == "programme":
        refresh_programme_activity()
    elif trigger == "all":
        load_or_refresh_all()

    if trigger:
        del st.session_state["trigger_reload"]


def refresh_leave_calendar():
    with sqlite3.connect(DB_PATH) as conn:
        st.session_state.leave_calendar_df = pd.read_sql("SELECT * FROM leave_calendar", conn)
    st.session_state.leave_calendar_df = parse_week_commencing(st.session_state.leave_calendar_df)


def refresh_onsite_calendar():
    with sqlite3.connect(DB_PATH) as conn:
        st.session_state.onsite_calendar_df = pd.read_sql("""
            SELECT staff_member, week_commencing, week_number, SUM(on_site_days) AS on_site_days
            FROM on_site_calendar
            GROUP BY staff_member, week_commencing, week_number
        """, conn)
    st.session_state.onsite_calendar_df = parse_week_commencing(st.session_state.onsite_calendar_df)


def refresh_programme_activity():
    with sqlite3.connect(DB_PATH) as conn:
        st.session_state.programme_calendar_df = pd.read_sql("SELECT * FROM programme_activity", conn)
    st.session_state.programme_calendar_df = parse_week_commencing(st.session_state.programme_calendar_df)

# --------------------------
# MAIN LOAD FUNCTION
# --------------------------
def load_or_refresh_all():

    with sqlite3.connect(DB_PATH) as conn:

        # ---------------------------
        # Load tables
        # ---------------------------
        staff_list = pd.read_sql("SELECT * FROM staff_list WHERE archive_flag = 0", conn)
        programme_list = pd.read_sql("SELECT * FROM programme_categories WHERE archive_flag = 0", conn)
        programme_calendar_df = pd.read_sql("SELECT * FROM programme_activity", conn)

        leave_calendar_df = pd.read_sql("""
            SELECT staff_member, week_commencing, week_number,
                   SUM(days_leave) AS days_leave
            FROM leave_calendar
            GROUP BY staff_member, week_commencing, week_number
        """, conn)

        onsite_calendar_df = pd.read_sql("""
            SELECT staff_member, week_commencing, week_number,
                   SUM(on_site_days) AS on_site_days
            FROM on_site_calendar
            GROUP BY staff_member, week_commencing, week_number
        """, conn)

    # ---------------------------
    # ✅ Ensure default_programme exists
    # ---------------------------
    if "default_programme" not in staff_list.columns:
        staff_list["default_programme"] = None

    staff_list["default_programme"] = (
        staff_list["default_programme"]
        .astype(str)
        .str.strip()
        .replace({"": None, "nan": None})
    )

    # ---------------------------
    # ✅ Validate against programme list
    # ---------------------------
    valid_programmes = set(
        programme_list["programme_categories"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    staff_list["default_programme"] = staff_list["default_programme"].apply(
        lambda x: x if x in valid_programmes else None
    )

    # ---------------------------
    # Parse dates
    # ---------------------------
    programme_calendar_df = parse_week_commencing(programme_calendar_df)
    leave_calendar_df = parse_week_commencing(leave_calendar_df)
    onsite_calendar_df = parse_week_commencing(onsite_calendar_df)

    # ---------------------------
    # Store base tables
    # ---------------------------
    st.session_state.staff_list = staff_list
    st.session_state.programme_list = programme_list
    st.session_state.programme_calendar_df = programme_calendar_df
    st.session_state.leave_calendar_df = leave_calendar_df
    st.session_state.onsite_calendar_df = onsite_calendar_df

    # ---------------------------
    # Lookup lists
    # ---------------------------
    st.session_state.staff_names = sorted(staff_list["staff_member"].dropna().unique())
    st.session_state.programme_names = sorted(programme_list["programme_categories"].dropna().unique())

    # ---------------------------
    # Programme totals
    # ---------------------------
    prog_staff_week = (
        programme_calendar_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(total_prog_hours=("activity_value", "sum"))
    )

    # ---------------------------
    # Leave totals
    # ---------------------------
    leave_calendar_df["leave_hours"] = leave_calendar_df["days_leave"].fillna(0) * 7.5

    leave_staff_week = (
        leave_calendar_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(total_leave_hours=("leave_hours", "sum"))
    )

    # ---------------------------
    # Staff capacity
    # ---------------------------
    staff_base = staff_list[["staff_member", "hours_pw", "deploy_ratio"]].copy()

    staff_week = prog_staff_week.merge(
        leave_staff_week,
        on=["staff_member", "week_commencing"],
        how="outer"
    ).merge(
        staff_base,
        on="staff_member",
        how="left"
    )

    staff_week = staff_week.fillna({
        "total_prog_hours": 0,
        "total_leave_hours": 0,
        "deploy_ratio": 1.0,
        "hours_pw": 37.5
    })

    staff_week["total_contr_hours"] = staff_week["hours_pw"]
    staff_week["total_avail_hours"] = (
        staff_week["total_contr_hours"] - staff_week["total_leave_hours"]
    ).clip(lower=0)

    staff_week["total_non_deploy_hours"] = (
        staff_week["total_avail_hours"] * (1 - staff_week["deploy_ratio"])
    )

    staff_week["total_util_hours"] = (
        staff_week["total_prog_hours"] + staff_week["total_non_deploy_hours"]
    )

    st.session_state.staff_week_capacity_df = staff_week

    # ---------------------------
    # Weekly summary
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
        )
        .sort_values("week_commencing")
    )

    weekly["util_rate"] = (
        (weekly["total_non_deploy_hours"] + weekly["total_prog_hours"])
        / weekly["total_avail_hours"]
        * 100
    ).fillna(0)

    weekly["util_target"] = target_util_rate

    st.session_state.staff_prog_pivot_df = weekly


