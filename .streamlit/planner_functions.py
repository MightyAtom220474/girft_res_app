import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
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
    highlight_current_week=True  # NEW: optional highlighting
    ):
    """
    Generates a 52-week heatmap for all staff, filling missing weeks with 0.
    Can optionally highlight the current week.
    """
    df = df.copy()

    # -----------------------------
    # Convert week_col to datetime.date
    # -----------------------------
    df[week_col] = pd.to_datetime(df[week_col], errors='coerce').dt.date

    # -----------------------------
    # Generate 52 Mondays (26 back, 26 forward)
    # -----------------------------
    today = date.today()
    start_monday = today - timedelta(weeks=26, days=today.weekday())
    week_commencings = [start_monday + timedelta(weeks=i) for i in range(52)]

    # -----------------------------
    # Full staff × week grid
    # -----------------------------
    staff_members = df[staff_col].unique()
    full_grid = pd.MultiIndex.from_product(
        [staff_members, week_commencings],
        names=[staff_col, week_col]
    ).to_frame(index=False)
    full_grid = full_grid.sort_values([staff_col, week_col]).reset_index(drop=True)
    full_grid['week_number'] = full_grid.groupby(staff_col).cumcount() + 1

    # -----------------------------
    # Merge with existing data
    # -----------------------------
    df_full = full_grid.merge(
        df[[staff_col, week_col, value_col]],
        on=[staff_col, week_col],
        how='left'
    )
    df_full[value_col] = df_full[value_col].fillna(0).astype(int)

    # -----------------------------
    # Determine zmax
    # -----------------------------
    if zmax is None:
        zmax = df_full[value_col].max()

    # -----------------------------
    # Pivot for heatmap
    # -----------------------------
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

    # -----------------------------
    # Tick labels and current week index
    # -----------------------------
    ticktext = []
    current_idx = None
    current_week_start = today - timedelta(days=today.weekday())

    for i, c in enumerate(cols):
        # Ensure datetime.date
        c_date = pd.to_datetime(c).date() if isinstance(c, str) else c
        ticktext.append(c_date.strftime("%d-%b-%y"))
        if highlight_current_week and c_date == current_week_start:
            current_idx = i

    # -----------------------------
    # Build heatmap
    # -----------------------------
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_vals,
            y=y,
            colorscale=colorscale,
            zmin=0,
            zmax=zmax,
            colorbar=dict(title=colorbar_title),
            customdata=[[c.strftime("%d-%b-%y") for c in cols]] * len(y),
            hovertemplate=(
                "Staff: %{y}<br>"
                "Week Commencing: %{customdata}<br>"
                f"{colorbar_title}: %{z}<extra></extra>"
            ),
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

    # -----------------------------
    # Highlight current week safely
    # -----------------------------
    if highlight_current_week and current_idx is not None:
        fig.update_layout(
            shapes=[
                dict(
                    type="rect",
                    x0=current_idx - 0.5,
                    x1=current_idx + 0.5,
                    y0=-0.5,                   # start before first staff
                    y1=len(y)-0.5,             # end after last staff
                    xref="x",
                    yref="y",                  # now in data coordinates
                    fillcolor="black",
                    opacity=0.3,
                    line_width=5,              # optional: no border
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
