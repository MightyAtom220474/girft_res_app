import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash

from db import execute, query_df
import data_store as ds


# ============================================================
# CONSTANTS
# ============================================================
num_weeks = 52
year = 2025
decimals = 1


# ============================================================
# ACTIVITY CHART
# ============================================================
def make_activity_chart(activity_calendar_df, programme_names):

    plot_df = (
        activity_calendar_df
        .groupby(["week_number", "programme_category"], as_index=False)
        .agg(activity_value=("activity_value", "sum"))
        .pivot(
            index="week_number",
            columns="programme_category",
            values="activity_value"
        )
        .fillna(0)
        .sort_index()
    )

    fig = go.Figure()

    for programme in programme_names:
        if programme in plot_df.columns:
            fig.add_trace(go.Bar(
                x=plot_df.index,
                y=plot_df[programme],
                name=programme
            ))

    fig.update_layout(
        barmode="stack",
        xaxis_title="Week",
        yaxis_title="Hours"
    )

    return fig


# ============================================================
# ACCESS FILTER
# ============================================================
def filter_by_access(df, staff_col="staff_member"):

    access = st.session_state.access_level
    username = st.session_state.username

    if access in ("admin", "viewer"):
        return df

    if access == "user":
        return df[df["username"] == username]

    return df.iloc[0:0]


# ============================================================
# STAFF
# ============================================================
def update_staff_list(
    new_staff=None,
    job_role=None,
    hours_pw=None,
    leave_allowance_days=None,
    is_deployable=None,
    deploy_ratio=None,
    default_programme=None,
    username=None,
    password=None,
    user_access=None
):

    if not new_staff:
        return

    hashed_pw = generate_password_hash(password) if password else None

    execute("""
        INSERT INTO staff_list (
            staff_member,
            job_role,
            hours_pw,
            leave_allowance_days,
            is_deployable,
            deploy_ratio,
            default_programme,
            username,
            password,
            access_level,
            archive_flag
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        ON CONFLICT (staff_member)
        DO UPDATE SET
            job_role = EXCLUDED.job_role,
            hours_pw = EXCLUDED.hours_pw,
            leave_allowance_days = EXCLUDED.leave_allowance_days,
            is_deployable = EXCLUDED.is_deployable,
            deploy_ratio = EXCLUDED.deploy_ratio,
            default_programme = EXCLUDED.default_programme,
            username = EXCLUDED.username,
            password = EXCLUDED.password,
            access_level = EXCLUDED.access_level
    """, (
        new_staff,
        job_role,
        hours_pw,
        leave_allowance_days,
        int(is_deployable) if is_deployable is not None else None,
        deploy_ratio,
        default_programme,
        username,
        hashed_pw,
        user_access
    ))


def restore_staff(staff_member):

    execute("""
        UPDATE staff_list
        SET archive_flag = 0
        WHERE staff_member = %s
    """, (staff_member,))


def update_password(username, new_password):

    hashed_password = generate_password_hash(new_password)

    execute("""
        UPDATE staff_list
        SET password = %s,
            must_change_password = 0
        WHERE username = %s
    """, (hashed_password, username))


# ============================================================
# PROGRAMME
# ============================================================
def update_programme_list(new_programme=None, programme_type=None, programme_group=None):

    if not new_programme:
        return

    execute("""
        INSERT INTO programme_categories (
            programme_category,
            programme_type,
            programme_group,
            archive_flag
        )
        VALUES (%s, %s, %s, 0)
        ON CONFLICT (programme_category)
        DO UPDATE SET
            programme_type = EXCLUDED.programme_type,
            programme_group = EXCLUDED.programme_group
    """, (new_programme, programme_type, programme_group))


# ============================================================
# PROGRAMME ACTIVITY
# ============================================================
def save_programme_activity(
    selected_staff,
    week_commencing,
    activity_inputs,
    repeat_weeks=1
):

    base_week = pd.to_datetime(week_commencing)

    for week_offset in range(repeat_weeks):

        current_week = base_week + timedelta(weeks=week_offset)
        week_number = int(current_week.isocalendar().week)

        execute("""
            DELETE FROM programme_activity
            WHERE staff_member = %s
            AND week_commencing = %s
        """, (selected_staff, current_week.date()))

        for programme, hours in activity_inputs.items():

            if float(hours) <= 0:
                continue

            execute("""
                INSERT INTO programme_activity (
                    staff_member,
                    programme_category,
                    activity_value,
                    week_commencing,
                    week_number
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                selected_staff,
                programme,
                float(hours),
                current_week.date(),
                week_number
            ))


# ============================================================
# LEAVE
# ============================================================
def save_annual_leave(staff_member, week_commencing, days_leave):

    week_commencing = pd.to_datetime(week_commencing)
    week_number = int(week_commencing.isocalendar().week)

    execute("""
        INSERT INTO leave_calendar (
            staff_member,
            week_commencing,
            week_number,
            days_leave,
            updated_at
        )
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (staff_member, week_commencing)
        DO UPDATE SET
            days_leave = EXCLUDED.days_leave,
            week_number = EXCLUDED.week_number,
            updated_at = CURRENT_TIMESTAMP
    """, (
        staff_member,
        week_commencing.date(),
        week_number,
        days_leave
    ))


# ============================================================
# ON SITE
# ============================================================
def save_on_site(staff_member, programme_category, week_commencing, on_site_days):

    week_commencing = pd.to_datetime(week_commencing)
    week_number = int(week_commencing.isocalendar().week)

    execute("""
        INSERT INTO on_site_calendar (
            staff_member,
            programme_category,
            week_commencing,
            week_number,
            on_site_days,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (staff_member, programme_category, week_commencing)
        DO UPDATE SET
            on_site_days = EXCLUDED.on_site_days,
            week_number = EXCLUDED.week_number,
            updated_at = CURRENT_TIMESTAMP
    """, (
        staff_member,
        programme_category,
        week_commencing.date(),
        week_number,
        on_site_days
    ))


# ============================================================
# REFRESH FUNCTIONS
# ============================================================

# ============================================================
# TRIGGER RELOAD HANDLER
# ============================================================
def handle_trigger_reload():
    """
    Centralised reload handler for Streamlit session state triggers.
    """

    trigger = st.session_state.get("trigger_reload")

    if not trigger:
        return

    if trigger == "leave":
        refresh_leave_calendar()

    elif trigger == "onsite":
        refresh_onsite_calendar()

    elif trigger == "programme":
        refresh_programme_activity()

    elif trigger == "all":
        ds.load_or_refresh_all()

    # Clear trigger after handling
    del st.session_state["trigger_reload"]
def refresh_leave_calendar():
    df = query_df("SELECT * FROM leave_calendar")
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce")
    st.session_state.leave_calendar_df = df


def refresh_onsite_calendar():
    df = query_df("""
        SELECT staff_member,
               week_commencing,
               week_number,
               SUM(on_site_days) AS on_site_days
        FROM on_site_calendar
        GROUP BY staff_member, week_commencing, week_number
    """)
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce")
    st.session_state.onsite_calendar_df = df


def refresh_programme_activity():
    df = query_df("SELECT * FROM programme_activity")
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce")
    st.session_state.programme_calendar_df = df

# ============================================================
# DEFAULT PROGRAMME CLEANING
# ============================================================
def clean_default_programme_column(programme_df):
    """
    Ensures default_programme exists, is cleaned, and valid.
    """

    df = programme_df.copy()

    # Ensure column exists
    if "default_programme" not in df.columns:
        df["default_programme"] = None

    # Clean values
    df["default_programme"] = (
        df["default_programme"]
        .astype(str)
        .str.strip()
        .replace({"": None, "nan": None})
    )

    # Validate against actual programme list
    valid_programmes = set(
        programme_df["programme_category"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    df["default_programme"] = df["default_programme"].apply(
        lambda x: x if x in valid_programmes else None
    )

    return df

# ============================================================
# DEFAULT PROGRAMME HELPERS
# ============================================================

# ============================================================
# DEFAULT PROGRAMME CLEANING (FIXED FOR YOUR COLUMN)
# ============================================================
def clean_default_programme_column(programme_df):
    """
    Cleans and validates the default_programme column.
    Uses actual DB column: programme_categories
    """

    df = programme_df.copy()

    # ✅ Use your real column name
    programme_col = "programme_categories"

    if programme_col not in df.columns:
        raise KeyError(
            f"Column '{programme_col}' not found. Columns: {list(df.columns)}"
        )

    # --------------------------------------------------------
    # Ensure default_programme exists
    # --------------------------------------------------------
    if "default_programme" not in df.columns:
        df["default_programme"] = None

    # --------------------------------------------------------
    # Clean values
    # --------------------------------------------------------
    df["default_programme"] = (
        df["default_programme"]
        .astype(str)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )

    # --------------------------------------------------------
    # Validate against real programme list
    # --------------------------------------------------------
    valid_programmes = set(
        df[programme_col]
        .dropna()
        .astype(str)
        .str.strip()
    )

    df["default_programme"] = df["default_programme"].apply(
        lambda x: x if x in valid_programmes else None
    )

    return df

def get_default_programme_map(staff_df):
    return dict(zip(staff_df["staff_member"], staff_df["default_programme"]))


def get_deployable_hours_map(staff_df):
    df = staff_df.copy()
    df["hours_pw"] = df["hours_pw"].fillna(37.5)
    df["deploy_ratio"] = df["deploy_ratio"].fillna(1.0)
    df["deployable_hours"] = df["hours_pw"] * df["deploy_ratio"]
    return dict(zip(df["staff_member"], df["deployable_hours"]))


def calculate_default_hours_for_staff(staff_df, staff_member, pct=1.0):

    row = staff_df.loc[staff_df["staff_member"] == staff_member]

    if row.empty:
        return 0.0

    hours_pw = float(row.iloc[0].get("hours_pw", 37.5) or 37.5)
    deploy_ratio = float(row.iloc[0].get("deploy_ratio", 1.0) or 1.0)

    deployable_hours = hours_pw * deploy_ratio

    return round(deployable_hours * pct, 1)


# ============================================================
# DATA ENTRY STATUS
# ============================================================

def get_weekly_data_entry_status(staff_list, programme_calendar_df, leave_calendar_df, week_commencing):

    week_commencing = pd.to_datetime(week_commencing).date()

    programme_calendar_df = programme_calendar_df.copy()
    leave_calendar_df = leave_calendar_df.copy()

    programme_calendar_df["week_commencing"] = pd.to_datetime(programme_calendar_df["week_commencing"]).dt.date
    leave_calendar_df["week_commencing"] = pd.to_datetime(leave_calendar_df["week_commencing"]).dt.date

    df = staff_list.loc[
        staff_list["archive_flag"] == 0,
        ["staff_member"]
    ].copy()

    entered_staff = programme_calendar_df.loc[
        programme_calendar_df["week_commencing"] == week_commencing,
        "staff_member"
    ].dropna().unique()

    df["has_entered"] = df["staff_member"].isin(entered_staff)

    leave_summary = leave_calendar_df.loc[
        leave_calendar_df["week_commencing"] == week_commencing
    ]

    if not leave_summary.empty:
        leave_summary = leave_summary.groupby("staff_member")["days_leave"].sum().reset_index()
    else:
        leave_summary = pd.DataFrame(columns=["staff_member", "days_leave"])

    df = df.merge(leave_summary, on="staff_member", how="left")
    df["days_leave"] = df["days_leave"].fillna(0)

    df["on_full_leave"] = df["days_leave"] >= 5

    def get_status(row):
        if row["has_entered"]:
            return "Entered"
        elif row["on_full_leave"]:
            return "On Leave"
        else:
            return "Missing"

    df["status"] = df.apply(get_status, axis=1)
    df["needs_attention"] = ~df["has_entered"] & ~df["on_full_leave"]

    df = df.sort_values(["needs_attention", "staff_member"], ascending=[False, True])

    return df

def render_data_entry_checklist(df_flags):

    st.subheader("📋 Data Entry Checklist")

    def colour_row(row):
        if row["status"] == "Entered":
            return ["background-color: #d4edda"] * len(row)
        elif row["status"] == "On Leave":
            return ["background-color: #fff3cd"] * len(row)
        else:
            return ["background-color: #f8d7da"] * len(row)

    st.dataframe(df_flags.style.apply(colour_row, axis=1), use_container_width=True)

# ============================================================
# STAFF WEEK CAPACITY
# ============================================================
# ============================================================
# STAFF WEEK CAPACITY
# ============================================================
def build_staff_week_capacity(
    staff_df,
    programme_df,
    leave_df,
    onsite_df=None,
    target_util_rate=0.85
):
    """
    Builds weekly capacity per staff member.

    Returns:
        DataFrame with:
        - staff_member
        - week_commencing
        - deployable_hours
        - capacity_hours
        - leave_hours
        - available_hours
    """

    # --------------------------------------------------------
    # COPY INPUTS (safe)
    # --------------------------------------------------------
    staff_df = staff_df.copy()
    programme_df = programme_df.copy()
    leave_df = leave_df.copy()

    if onsite_df is not None:
        onsite_df = onsite_df.copy()

    # --------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------------
    for col in ["staff_member"]:
        if col not in staff_df.columns:
            raise KeyError(f"Missing '{col}' in staff_df")

    for col in ["staff_member", "week_commencing"]:
        if col not in programme_df.columns:
            raise KeyError(f"Missing '{col}' in programme_df")

    for col in ["staff_member", "week_commencing", "days_leave"]:
        if col not in leave_df.columns:
            raise KeyError(f"Missing '{col}' in leave_df")

    # --------------------------------------------------------
    # PARSE DATES
    # --------------------------------------------------------
    programme_df["week_commencing"] = pd.to_datetime(
        programme_df["week_commencing"], errors="coerce"
    )

    leave_df["week_commencing"] = pd.to_datetime(
        leave_df["week_commencing"], errors="coerce"
    )

    # --------------------------------------------------------
    # STAFF DEFAULTS
    # --------------------------------------------------------
    staff_df["hours_pw"] = staff_df.get("hours_pw", 37.5).fillna(37.5)
    staff_df["deploy_ratio"] = staff_df.get("deploy_ratio", 1.0).fillna(1.0)

    staff_df["deployable_hours"] = (
        staff_df["hours_pw"] * staff_df["deploy_ratio"]
    )

    # --------------------------------------------------------
    # GET UNIQUE WEEKS
    # --------------------------------------------------------
    weeks = (
        programme_df["week_commencing"]
        .dropna()
        .sort_values()
        .unique()
    )

    if len(weeks) == 0:
        # fallback if programme table empty
        weeks = (
            leave_df["week_commencing"]
            .dropna()
            .sort_values()
            .unique()
        )

    if len(weeks) == 0:
        # final fallback → return empty safely
        return pd.DataFrame(columns=[
            "staff_member",
            "week_commencing",
            "deployable_hours",
            "capacity_hours",
            "leave_hours",
            "available_hours"
        ])

    # --------------------------------------------------------
    # BUILD BASE GRID (staff x weeks)
    # --------------------------------------------------------
    base = pd.MultiIndex.from_product(
        [staff_df["staff_member"], weeks],
        names=["staff_member", "week_commencing"]
    ).to_frame(index=False)

    # --------------------------------------------------------
    # MERGE STAFF DATA
    # --------------------------------------------------------
    base = base.merge(
        staff_df[["staff_member", "deployable_hours"]],
        on="staff_member",
        how="left"
    )

    # --------------------------------------------------------
    # AGGREGATE LEAVE
    # --------------------------------------------------------
    leave_summary = (
        leave_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(days_leave=("days_leave", "sum"))
    )

    base = base.merge(
        leave_summary,
        on=["staff_member", "week_commencing"],
        how="left"
    )

    base["days_leave"] = base["days_leave"].fillna(0)

    # --------------------------------------------------------
    # CONVERT LEAVE TO HOURS
    # --------------------------------------------------------
    base["leave_hours"] = (
        base["days_leave"] / 5.0 * base["deployable_hours"]
    )

    # --------------------------------------------------------
    # CAPACITY CALCULATION
    # --------------------------------------------------------
    base["capacity_hours"] = (
        base["deployable_hours"] * target_util_rate
    )

    # --------------------------------------------------------
    # AVAILABLE HOURS
    # --------------------------------------------------------
    base["available_hours"] = (
        base["capacity_hours"] - base["leave_hours"]
    )

    # Prevent negative values
    base["available_hours"] = base["available_hours"].clip(lower=0)

    # --------------------------------------------------------
    # FINAL SORT
    # --------------------------------------------------------
    base = base.sort_values(
        ["staff_member", "week_commencing"]
    ).reset_index(drop=True)

    return base

# ============================================================
# MONTHLY SUMMARY (BY STAFF)
# ============================================================
def build_monthly_summary(staff_week_df, weekly_df):
    """
    Builds monthly summary per staff member.

    Inputs:
        staff_week_df : output of build_staff_week_capacity
        weekly_df     : output of build_weekly_summary

    Returns:
        DataFrame grouped by:
        - staff_member
        - month
    """

    df = staff_week_df.copy()

    # --------------------------------------------------------
    # SAFETY CHECKS
    # --------------------------------------------------------
    required_cols = [
        "staff_member",
        "week_commencing",
        "capacity_hours",
        "available_hours",
        "leave_hours"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing column '{col}' in staff_week_df")

    # --------------------------------------------------------
    # ADD MONTH COLUMN
    # --------------------------------------------------------
    df["week_commencing"] = pd.to_datetime(
        df["week_commencing"], errors="coerce"
    )

    df["month"] = df["week_commencing"].dt.to_period("M").astype(str)

    # --------------------------------------------------------
    # AGGREGATE PER STAFF PER MONTH
    # --------------------------------------------------------
    monthly = (
        df
        .groupby(["staff_member", "month"], as_index=False)
        .agg(
            total_capacity_hours=("capacity_hours", "sum"),
            total_available_hours=("available_hours", "sum"),
            total_leave_hours=("leave_hours", "sum")
        )
    )

    # --------------------------------------------------------
    # CALCULATE UTILISATION
    # --------------------------------------------------------
    monthly["utilisation_rate"] = (
        1 - (monthly["total_available_hours"] / monthly["total_capacity_hours"])
    )

    monthly["utilisation_rate"] = monthly["utilisation_rate"].replace(
        [np.inf, -np.inf], 0
    ).fillna(0)

    # --------------------------------------------------------
    # SORT CLEANLY
    # --------------------------------------------------------
    monthly = monthly.sort_values(
        ["staff_member", "month"]
    ).reset_index(drop=True)

    return monthly

# ============================================================
# MONTHLY CAPACITY SUMMARY (FIXED WITH total_util_hours)
# ============================================================
def build_monthly_capacity_df(staff_week_df, target_util_rate=0.85):

    import pandas as pd
    import numpy as np

    df = staff_week_df.copy()

    # --------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------------
    required_cols = [
        "staff_member",
        "week_commencing",
        "capacity_hours",
        "available_hours"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing column '{col}' in staff_week_df")

    # --------------------------------------------------------
    # DATE → MONTH
    # --------------------------------------------------------
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce")
    df["month"] = df["week_commencing"].dt.to_period("M").dt.to_timestamp()

    # --------------------------------------------------------
    # AGGREGATE PER STAFF PER MONTH
    # --------------------------------------------------------
    monthly_staff_df = (
        df.groupby(["staff_member", "month"], as_index=False)
        .agg(
            total_contr_hours=("capacity_hours", "sum"),
            total_avail_hours=("available_hours", "sum")
        )
    )

    # --------------------------------------------------------
    # ✅ THIS WAS MISSING (CRITICAL FIX)
    # --------------------------------------------------------
    monthly_staff_df["total_util_hours"] = (
        monthly_staff_df["total_contr_hours"]
        - monthly_staff_df["total_avail_hours"]
    )

    # --------------------------------------------------------
    # UTIL %
    # --------------------------------------------------------
    monthly_staff_df["util_rate"] = (
        monthly_staff_df["total_util_hours"]
        / monthly_staff_df["total_contr_hours"]
    )

    monthly_staff_df["util_rate"] = (
        monthly_staff_df["util_rate"]
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        * 100
    )

    # --------------------------------------------------------
    # OVERALL MONTHLY TOTALS (FOR DASHBOARD)
    # --------------------------------------------------------
    monthly_df = (
        monthly_staff_df
        .groupby("month", as_index=False)
        .agg(
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_util_hours=("total_util_hours", "sum")
        )
    )

    # --------------------------------------------------------
    # FINAL UTIL %
    # --------------------------------------------------------
    monthly_df["util_rate"] = (
        monthly_df["total_util_hours"]
        / monthly_df["total_contr_hours"]
    )

    monthly_df["util_rate"] = (
        monthly_df["util_rate"]
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        * 100
    )

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------
    monthly_df["util_target"] = target_util_rate * 100

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------
    monthly_df = monthly_df.sort_values("month").reset_index(drop=True)
    monthly_staff_df = monthly_staff_df.sort_values(
        ["staff_member", "month"]
    ).reset_index(drop=True)

    
    today = date.today()

    window_start = pd.Timestamp(today - relativedelta(months=6))
    window_end   = pd.Timestamp(today + relativedelta(months=6))

    monthly_df = monthly_df[
        (monthly_df["month"] >= window_start) &
        (monthly_df["month"] <= window_end)
    ].copy()

    monthly_staff_df = monthly_staff_df[
        (monthly_staff_df["month"] >= window_start) &
        (monthly_staff_df["month"] <= window_end)
    ].copy()


    return monthly_df, monthly_staff_df

# ============================================================
# WEEKLY SUMMARY
# ============================================================
def build_weekly_summary(staff_week_df, target_util_rate=0.85):
    """
    Aggregates weekly capacity + availability across all staff.

    Returns:
        DataFrame with:
        - week_commencing
        - total_capacity_hours
        - total_available_hours
        - total_leave_hours
        - utilisation_rate
    """

    df = staff_week_df.copy()

    # --------------------------------------------------------
    # Safety checks
    # --------------------------------------------------------
    required_cols = [
        "week_commencing",
        "capacity_hours",
        "available_hours",
        "leave_hours"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing column '{col}' in staff_week_df")

    # --------------------------------------------------------
    # Aggregate per week
    # --------------------------------------------------------
    weekly = (
        df
        .groupby("week_commencing", as_index=False)
        .agg(
            total_capacity_hours=("capacity_hours", "sum"),
            total_available_hours=("available_hours", "sum"),
            total_leave_hours=("leave_hours", "sum")
        )
        .sort_values("week_commencing")
    )

    # --------------------------------------------------------
    # Utilisation
    # --------------------------------------------------------
    weekly["utilisation_rate"] = (
        1 - (weekly["total_available_hours"] / weekly["total_capacity_hours"])
    )

    # Handle divide-by-zero safely
    weekly["utilisation_rate"] = weekly["utilisation_rate"].replace([np.inf, -np.inf], 0)
    weekly["utilisation_rate"] = weekly["utilisation_rate"].fillna(0)

    # --------------------------------------------------------
    # Target comparison (useful for dashboard)
    # --------------------------------------------------------
    weekly["target_utilisation"] = target_util_rate
    weekly["variance_to_target"] = (
        weekly["utilisation_rate"] - target_util_rate
    )

    return weekly

# ============================================================
# CLEAN PROGRAMME GROUP
# ============================================================
def clean_programme(value):
    """
    Cleans programme group names for consistency.
    """

    if value is None:
        return None

    value = str(value).strip()

    if value == "" or value.lower() == "nan":
        return None

    # Standardise formatting
    value = value.replace(" and ", " & ")
    value = value.title()

    return value

# ============================================================
# 52-WEEK HEATMAP
# ============================================================
def create_52week_heatmap(
    df,
    value_col,
    title=None,
    colorscale="Viridis",
    colorbar_title="Value",
    zmax=5,
    highlight_current_week=True
):
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from datetime import date, timedelta

    data = df.copy()

    # --------------------------------------------------------
    # Ensure date format
    # --------------------------------------------------------
    data["week_commencing"] = pd.to_datetime(
        data["week_commencing"], errors="coerce"
    )

    # --------------------------------------------------------
    # Create week index (relative)
    # --------------------------------------------------------
    today = date.today()
    current_week = today - timedelta(days=today.weekday())

    # relative week index
    data["week_index"] = (
        (data["week_commencing"] - pd.Timestamp(current_week)) / np.timedelta64(1, 'W')
    ).astype(int)

    # --------------------------------------------------------
    # Pivot for heatmap
    # --------------------------------------------------------
    pivot = data.pivot_table(
        index="staff_member",
        columns="week_index",
        values=value_col,
        aggfunc="sum",
        fill_value=0
    )

    pivot = pivot.sort_index()

    # --------------------------------------------------------
    # Build heatmap
    # --------------------------------------------------------
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=colorscale,
        zmin=0,
        zmax=zmax,
        colorbar=dict(title=colorbar_title)
    ))

    # --------------------------------------------------------
    # Highlight current week
    # --------------------------------------------------------
    if highlight_current_week and 0 in pivot.columns:
        fig.add_shape(
            type="rect",
            x0=-0.5,
            x1=0.5,
            y0=-0.5,
            y1=len(pivot.index) - 0.5,
            line=dict(color="black", width=2),
            fillcolor="rgba(0,0,0,0)"
        )

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------
    fig.update_layout(
        title=title,
        xaxis_title="Week",
        yaxis_title="Staff",
        height=500
    )

    return fig
