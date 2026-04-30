import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import re
#import os
from datetime import date, timedelta
# import data_store as ds
from werkzeug.security import generate_password_hash
#import matplotlib.pyplot as plt
import plotly.graph_objects as go
#import numpy as np
from data_store import DB_PATH

num_weeks = 52
year = 2025   # you can make this a user input if you want
decimals = 1 # number of decimal places


def make_activity_chart(activity_calendar_df, programme_names):
    import plotly.graph_objects as go

    # Pivot normalised data → wide just for plotting
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
            fig.add_trace(
                go.Bar(
                    x=plot_df.index,
                    y=plot_df[programme],
                    name=programme
                )
            )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Week",
        yaxis_title="Hours"
    )

    return fig

# function to dynamically change what users can view based on their access level
def filter_by_access(df, staff_col="staff_member"):
    access = st.session_state.access_level
    username = st.session_state.username

    # Admins and viewers see everything
    if access in ("admin", "viewer"):
        return df

    # Users only see their own rows
    if access == "user":
        return df[df["username"] == username]

    # Safety fallback
    return df.iloc[0:0]

##### Functions to interact with SQLite database #####

def update_staff_list(
    new_staff=None,
    job_role=None,
    hours_pw=None,
    leave_allowance_days=None,
    is_deployable=None,
    deploy_ratio=None,
    username=None,
    password=None,
    user_access=None
    ):
    """
    Update staff_list table in SQLite.
    """

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # --- ADD NEW STAFF MEMBER ---
        if new_staff:
            cursor.execute("""
                    INSERT INTO staff_list (
                        staff_member,
                        job_role,
                        hours_pw,
                        leave_allowance_days,
                        is_deployable,
                        deploy_ratio,
                        username,
                        password,
                        access_level,
                        archive_flag
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(staff_member)
                    DO UPDATE SET
                        job_role = excluded.job_role,
                        hours_pw = excluded.hours_pw,
                        leave_allowance_days = excluded.leave_allowance_days,
                        is_deployable = excluded.is_deployable,
                        deploy_ratio = excluded.deploy_ratio,
                        username = excluded.username,
                        password = excluded.password,
                        access_level = excluded.access_level
                    """, (
                        new_staff,
                        job_role,
                        hours_pw,
                        leave_allowance_days,
                        int(is_deployable) if is_deployable is not None else None,
                        deploy_ratio,
                        username,
                        password,
                        user_access
                    ))
        
def update_programme_list(
    new_programme=None,
    programme_type=None,
    programme_group=None
    #archive_programme=None
    ):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        if new_programme:
            cursor.execute(
                """
                INSERT OR IGNORE INTO programme_categories (
                    programme_categories,
                    programme_type,
                    programme_group,
                    archive_flag
                )
                VALUES (?, ?, ?, 0)
                """,
                (new_programme, programme_type, programme_group)
            )

        # if archive_programme:
        #     cursor.execute(
        #         """
        #         UPDATE programme_categories
        #         SET archive_flag = 1
        #         WHERE programme_categories = ?
        #         """,
        #         (archive_programme,)
        #     )

        # conn.commit()


def update_password(conn, username, new_password):
    """
    Update a user's password and clear must_change_password flag
    """

    hashed_password = generate_password_hash(new_password)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE staff_list
            SET password = ?,
                must_change_password = 0
            WHERE username = ?
            """,
            (hashed_password, username)
        )

        conn.commit()
        #conn.close()

def restore_staff(conn, staff_member):
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE staff_list SET archive_flag = 0 WHERE staff_member = ?",
            (staff_member,)
        )
        conn.commit()
        #conn.close()

def save_programme_activity(
    selected_staff,
    week_commencing,
    activity_inputs
    ):
    week_dt = pd.to_datetime(week_commencing)
    week_number = int(week_dt.isocalendar().week)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()


        for programme_category, activity_value in activity_inputs.items():
            cursor.execute(
                """
                INSERT INTO programme_activity (
                    staff_member,
                    week_commencing,
                    week_number,
                    programme_category,
                    activity_value,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(staff_member, week_commencing, programme_category)
                DO UPDATE SET
                    activity_value = excluded.activity_value,
                    week_number = excluded.week_number,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    selected_staff,
                    week_dt.date(),
                    week_number,
                    programme_category,
                    activity_value
                )
            )

        conn.commit()
        #conn.close()

def save_annual_leave(staff_member, week_commencing, days_leave):
    week_commencing = pd.to_datetime(week_commencing)
    week_number = int(week_commencing.isocalendar().week)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO leave_calendar (
                staff_member,
                week_commencing,
                week_number,
                days_leave,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(staff_member, week_commencing)
            DO UPDATE SET
                days_leave = excluded.days_leave,
                week_number = excluded.week_number,
                updated_at = CURRENT_TIMESTAMP
        """, (
            staff_member,
            week_commencing.date(),
            week_number,
            days_leave
        ))

        conn.commit()
        #conn.close()

def save_on_site(staff_member, programme_category, week_commencing, on_site_days):
    week_commencing = pd.to_datetime(week_commencing)
    week_number = int(week_commencing.isocalendar().week)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO on_site_calendar (
                staff_member,
                programme_category,
                week_commencing,
                week_number,
                on_site_days,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(staff_member, programme_category, week_commencing)
            DO UPDATE SET
                on_site_days = excluded.on_site_days,
                week_number = excluded.week_number,
                updated_at = CURRENT_TIMESTAMP
        """, (
            staff_member,
            programme_category,
            week_commencing.date(),
            week_number,
            on_site_days
        ))
        conn.commit()

# ------------------------------------------------
# Helper function to create heatmaps
# ------------------------------------------------

def create_52week_heatmap(
    df,
    staff_col='staff_member',
    week_col='week_commencing',
    value_col='value',
    title="Staff Weekly Heatmap",
    colorscale="YlGnBu",
    colorbar_title="Value",
    zmax=None,
    highlight_current_week=True  # toggle highlight
    ):
    """
    Generates a 52-week heatmap for all staff with optional current week highlight
    and hover text disabled.
    """

    df = df.copy()

    # Convert week_col to datetime.date
    df[week_col] = pd.to_datetime(df[week_col], errors='coerce').dt.date

    # Generate 52 Mondays (26 back, 26 forward)
    today = date.today()
    start_monday = today - timedelta(weeks=26, days=today.weekday())
    week_commencings = [start_monday + timedelta(weeks=i) for i in range(52)]

    # Full staff × week grid
    staff_members = df[staff_col].unique()
    full_grid = pd.MultiIndex.from_product(
        [staff_members, week_commencings],
        names=[staff_col, week_col]
    ).to_frame(index=False)
    full_grid = full_grid.sort_values([staff_col, week_col]).reset_index(drop=True)
    full_grid['week_number'] = full_grid.groupby(staff_col).cumcount() + 1

    # Merge with existing data
    df_full = full_grid.merge(
        df[[staff_col, week_col, value_col]],
        on=[staff_col, week_col],
        how='left'
    )
    df_full[value_col] = df_full[value_col].fillna(0).astype(int)

    # Determine zmax
    if zmax is None:
        zmax = df_full[value_col].max()

    # Pivot for heatmap
    pivot = df_full.pivot_table(
        index=staff_col,
        columns=week_col,
        values=value_col,
        fill_value=0
    )

    z = pivot.to_numpy()
    y = pivot.index.astype(str).tolist()
    cols = list(pivot.columns)
    x_vals = list(range(len(cols)))

    # Tick labels and current week index
    ticktext = []
    current_idx = None
    current_week_start = today - timedelta(days=today.weekday())

    for i, c in enumerate(cols):
        c_date = pd.to_datetime(c).date() if isinstance(c, str) else c
        ticktext.append(c_date.strftime("%d-%b-%y"))
        if highlight_current_week and c_date == current_week_start:
            current_idx = i

    # Build heatmap with hover disabled
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_vals,
            y=y,
            colorscale=colorscale,
            zmin=0,
            zmax=zmax,
            colorbar=dict(title=colorbar_title),
            hoverinfo='skip',       # disables hover
            hovertemplate=None       # ensures hover template is ignored
        )
    )

    fig.update_layout(
        title=title,
        xaxis=dict(
            tickmode="array",
            tickvals=x_vals,
            ticktext=ticktext,
            tickangle=90,
        ),
        yaxis=dict(automargin=True),
        margin=dict(l=160, r=20, t=40, b=120),
        height=max(350, pivot.shape[0] * 20 + 160),
        showlegend=False,
    )

    # Highlight current week column fully behind heatmap
    if highlight_current_week and current_idx is not None:
        fig.update_layout(
            shapes=[
                dict(
                    type="rect",
                    x0=current_idx - 0.5,
                    x1=current_idx + 0.5,
                    y0=-0.5,           
                    y1=len(y)-0.5,     
                    xref="x",
                    yref="y",          
                    fillcolor="black",    
                    opacity=0.3,           
                    line_width=5,        
                    layer="above",      
                )
            ]
        )

    return fig

def create_heatmap(
    df,
    value_col,
    title,
    colorscale,
    colorbar_title,
    zmax,
    current_week_start=None
    ):
    """Build a standardized Plotly heatmap used in dashboard pages."""
    MAX_DAYS = zmax
    if current_week_start is None:
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
    df = df.copy()
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce").dt.date
    pivot = df.pivot_table(
        index="staff_member",
        columns="week_commencing",
        values=value_col,
        fill_value=0
    )
    z = pivot.to_numpy()
    y = pivot.index.astype(str).tolist()
    cols = list(pivot.columns)
    x_vals = list(range(len(cols)))
    ticktext = []
    current_idx = None
    for i, c in enumerate(cols):
        if hasattr(c, "date"):
            c_date = c.date()
            ticktext.append(c.strftime("%d-%b-%y"))
            if c_date == current_week_start:
                current_idx = i
        else:
            ticktext.append(str(c))
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_vals,
            y=y,
            colorscale=colorscale,
            zmin=0,
            zmax=MAX_DAYS,
            colorbar=dict(title=colorbar_title),
            customdata=[[c.strftime("%d-%b-%y") for c in cols]] * len(y),
            hovertemplate=(
                "Staff: %{y}<br>"
                "Week Commencing: %{customdata}<br>"
                f"{colorbar_title}: " + "%{z:.1f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=x_vals,
            ticktext=ticktext,
            tickangle=90,
        ),
        yaxis=dict(automargin=True),
        margin=dict(l=160, r=20, t=40, b=120),
        height=max(350, pivot.shape[0] * 20 + 160),
        showlegend=False,
    )
    if current_idx is not None:
        fig.add_vrect(
            x0=current_idx - 0.5,
            x1=current_idx + 0.5,
            xref="x",
            yref="paper",
            fillcolor="rgba(0,0,0,0.12)",
            opacity=0.15,
            line_width=2,
            line_color="black",
            layer="below",
        )
    return fig

def preview_colorscale(colorscale, title="Color Preview", n=100):
    """Show a horizontal bar preview of a given colorscale."""
    z = np.tile(np.linspace(0, 1, n), (10, 1))
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            colorscale=colorscale,
            showscale=False
        )
    )
    fig.update_layout(
        title={"text": title, "x": 0.5},
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        height=100,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

def clean_programme(text):
    if pd.isna(text):
        return text

    # Step 1: Replace standalone "and" with "&" (case-insensitive)
    text = re.sub(r'\band\b', '&', text, flags=re.IGNORECASE)

    # Step 2: Split text into words
    words = text.split()

    cleaned_words = []
    for w in words:
        # If word is all uppercase (acronym), keep it as is
        if w.isupper():
            cleaned_words.append(w)
        else:
            # Otherwise capitalize first letter
            cleaned_words.append(w.capitalize())

    return ' '.join(cleaned_words)

def get_inactive_staff_with_reasons(
    staff_list,
    programme_calendar_df,
    leave_calendar_df
    ):
    # -----------------------------
    # Previous week (Monday)
    # -----------------------------
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    previous_week_start = current_week_start - timedelta(weeks=1)

    # -----------------------------
    # Standardise dates
    # -----------------------------
    programme_calendar_df = programme_calendar_df.copy()
    leave_calendar_df = leave_calendar_df.copy()

    programme_calendar_df['week_commencing'] = pd.to_datetime(
        programme_calendar_df['week_commencing']
    ).dt.date

    leave_calendar_df['week_commencing'] = pd.to_datetime(
        leave_calendar_df['week_commencing']
    ).dt.date

    # -----------------------------
    # Active staff only
    # -----------------------------
    df = staff_list.loc[
        staff_list['archive_flag'] == 0,
        ['staff_member']
    ].copy()

    # -----------------------------
    # Activity last week (>0 only)
    # -----------------------------
    active_last_week = programme_calendar_df.loc[
        (programme_calendar_df['week_commencing'] == previous_week_start) &
        (programme_calendar_df['activity_value'].fillna(0) > 0),
        'staff_member'
    ].unique()

    df['no_activity_last_week'] = ~df['staff_member'].isin(active_last_week)

    # -----------------------------
    # Leave last week
    # -----------------------------
    leave_last_week = leave_calendar_df.loc[
        leave_calendar_df['week_commencing'] == previous_week_start
    ]

    leave_summary = (
        leave_last_week
        .assign(value=lambda x: x['days_leave'].fillna(0))
        .groupby('staff_member')['days_leave']
        .sum()
        .reset_index()
        #.rename(columns={'value': 'days_leave'})
        )

    df = df.merge(leave_summary, on='staff_member', how='left')
    df['days_leave'] = df['days_leave'].fillna(0)

    df['full_week_leave'] = df['days_leave'] >= 5

    # -----------------------------
    # Reason logic
    # -----------------------------
    def get_reason(row):
        if row['no_activity_last_week'] and not row['full_week_leave']:
            return "No activity recorded"
        elif row['full_week_leave']:
            return "On leave (5+ days)"
        else:
            return "OK"

    df['reason'] = df.apply(get_reason, axis=1)

    # -----------------------------
    # Final follow-up flag
    # -----------------------------
    df['needs_follow_up'] = (
        df['no_activity_last_week'] &
        (~df['full_week_leave'])
    )

    return df.sort_values(['needs_follow_up', 'staff_member'], ascending=[False, True]).reset_index(drop=True)

def render_followup_warning(df_flags):
    # Filter staff needing follow-up
    follow_up_df = df_flags[df_flags['needs_follow_up']]

    if follow_up_df.empty:
        st.success("✅ All staff have recorded activity for last week")
        return

    # -----------------------------
    # Warning header
    # -----------------------------
    st.error(f"🚨 {len(follow_up_df)} staff member(s) need to record activity for last week")

    # -----------------------------
    # Clean list display
    # -----------------------------
    names = ", ".join(follow_up_df['staff_member'].tolist())
    st.markdown(f"**Staff to follow up:** {names}")

    # -----------------------------
    # Expandable detail view
    # -----------------------------
    with st.expander("View details"):
        display_df = follow_up_df[
            ['staff_member', 'days_leave', 'reason']
        ].rename(columns={
            'staff_member': 'Staff Member',
            'days_leave': 'Leave Days',
            'reason': 'Status'
        })

        st.dataframe(display_df, use_container_width=True)

def get_default_programme_map(staff_df):
    return dict(
        zip(
            staff_df["staff_member"],
            staff_df.get("default_programme", [None] * len(staff_df))
        )
    )

def get_deployable_hours_map(staff_df):
    df = staff_df.copy()

    df["hours_pw"] = df["hours_pw"].fillna(37.5)
    df["deploy_ratio"] = df["deploy_ratio"].fillna(1.0)

    df["deployable_hours"] = df["hours_pw"] * df["deploy_ratio"]

    return dict(zip(df["staff_member"], df["deployable_hours"]))

def calculate_default_hours_for_staff(staff_df, staff_member, pct=0.8):
    """
    Looks up staff member and calculates default hours.
    """

    row = staff_df.loc[staff_df["staff_member"] == staff_member]

    if row.empty:
        return 0.0

    hours_pw = float(row.iloc[0].get("hours_pw", 37.5) or 37.5)
    deploy_ratio = float(row.iloc[0].get("deploy_ratio", 1.0) or 1.0)

    deployable_hours = hours_pw * deploy_ratio

    return round(deployable_hours * pct, 1)
