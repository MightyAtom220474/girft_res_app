import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta
# import sqlite3
import streamlit as st
#import os
import planner_functions as pf
# from config import DB_PATH
from db import execute, query_df

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")

target_util_rate = 85
default_password = 'Temporary123!'

# staff_list = None
# programme_list = None
# programme_categories = None
# programme_calendar_df = None
# leave_calendar_df = None
# onsite_calendar_df = None
# staff_leave_merged_df = None
# staff_prog_merged_df = None
# staff_prog_combined_df = None
# staff_detail_monthly_df = None
# staff_prog_pivot_df = None
# staff_leave_df = None
# programme_names = None
# staff_names = None

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


def load_or_refresh_all():
    import pandas as pd
    import streamlit as st

    # ✅ Set target utilisation rate
    target_util_rate = 0.85

    # -----------------------------
    # Initialise session state
    # -----------------------------
    defaults = {
        "staff_list": pd.DataFrame(),
        "programme_list": pd.DataFrame(),
        "programme_calendar_df": pd.DataFrame(),
        "leave_calendar_df": pd.DataFrame(),
        "onsite_calendar_df": pd.DataFrame(),
        "staff_week_capacity_df": pd.DataFrame(),
        "staff_prog_pivot_df": pd.DataFrame(),
        "staff_prog_monthly_df": pd.DataFrame(),
        "staff_detail_monthly_df": pd.DataFrame(),
        "staff_summary_monthly_df": pd.DataFrame(),  # ✅ new (avoid overwrite bug)
        "programme_names": [],
        "staff_names": []
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # -----------------------------
    # LOAD DATA FROM DB
    # -----------------------------
    st.session_state.staff_list = query_df("""
        SELECT *
        FROM staff_list
        WHERE archive_flag = 0
    """)

    st.session_state.programme_list = query_df("""
        SELECT *
        FROM programme_categories
        WHERE archive_flag = 0
    """)

    st.session_state.programme_calendar_df = query_df("""
        SELECT *
        FROM programme_activity
    """)

    st.session_state.leave_calendar_df = query_df("""
        SELECT
            staff_member,
            week_commencing,
            week_number,
            SUM(days_leave) AS days_leave
        FROM leave_calendar
        GROUP BY staff_member, week_commencing, week_number
    """)

    st.session_state.onsite_calendar_df = query_df("""
        SELECT
            staff_member,
            week_commencing,
            week_number,
            SUM(on_site_days) AS on_site_days
        FROM on_site_calendar
        GROUP BY staff_member, week_commencing, week_number
    """)

    # -----------------------------
    # ✅ Pull into local variables (FIX)
    # -----------------------------
    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df
    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df

    # -----------------------------
    # ✅ DEFAULT PROGRAMME CLEANING
    # -----------------------------
    programme_list = pf.clean_default_programme_column(programme_list)

    # -----------------------------
    # Parse dates
    # -----------------------------
    programme_calendar_df = parse_week_commencing(programme_calendar_df)
    leave_calendar_df = parse_week_commencing(leave_calendar_df)
    onsite_calendar_df = parse_week_commencing(onsite_calendar_df)

    # -----------------------------
    # Store cleaned tables back
    # -----------------------------
    st.session_state.staff_list = staff_list
    st.session_state.programme_list = programme_list
    st.session_state.programme_calendar_df = programme_calendar_df
    st.session_state.leave_calendar_df = leave_calendar_df
    st.session_state.onsite_calendar_df = onsite_calendar_df

    # -----------------------------
    # Lookup lists
    # -----------------------------
    st.session_state.staff_names = sorted(
        staff_list["staff_member"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    st.session_state.programme_names = sorted(
        programme_list["programme_categories"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    # -----------------------------
    # Capacity calculations
    # -----------------------------
    
    staff_week = pf.build_staff_week_capacity(
        staff_list,
        programme_calendar_df,
        leave_calendar_df
    )

    weekly = pf.build_weekly_summary(
        staff_week,
        target_util_rate
    )

    monthly_by_staff = pf.build_monthly_summary(
        staff_week,
        weekly
    )

    # -----------------------------
    # Store outputs
    # -----------------------------
    st.session_state.staff_week_capacity_df = staff_week
    st.session_state.staff_prog_pivot_df = weekly
    st.session_state.staff_summary_monthly_df = monthly_by_staff  # ✅ fixed name

    # -----------------------------
    # Monthly capacity breakdown
    # -----------------------------
    monthly_df, monthly_staff_df = pf.build_monthly_capacity_df(
        staff_week,
        target_util_rate
    )

    st.session_state.staff_prog_monthly_df = monthly_df
    st.session_state.staff_detail_monthly_df = monthly_staff_df


