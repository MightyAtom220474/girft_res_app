import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import date, timedelta
import data_store as ds
from werkzeug.security import generate_password_hash
#import matplotlib.pyplot as plt
import plotly.graph_objects as go
#import numpy as np

num_weeks = 52
year = 2025   # you can make this a user input if you want
decimals = 1 # number of decimal places

DB_PATH = "girft_capacity_planner.db"

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

def save_on_site(staff_member, week_commencing, on_site_days):
    week_commencing = pd.to_datetime(week_commencing)
    week_number = int(week_commencing.isocalendar().week)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO on_site_calendar (
                staff_member,
                week_commencing,
                week_number,
                on_site_days,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(staff_member, week_commencing)
            DO UPDATE SET
                on_site_days = excluded.on_site_days,
                week_number = excluded.week_number,
                updated_at = CURRENT_TIMESTAMP
        """, (
            staff_member,
            week_commencing.date(),
            week_number,
            on_site_days
        ))

        conn.commit()
        #conn.close()
