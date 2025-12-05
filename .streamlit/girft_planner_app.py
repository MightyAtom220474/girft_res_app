import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np

num_weeks = 52
year = 2025   # you can make this a user input if you want
decimals = 1 # number of decimal places

st.set_page_config(page_title="Weekly Leave Planner", layout="wide")

# load up staff data file
def load_data(file_name):
    # if os.path.exists(staff_base_data):
    df = pd.read_csv(file_name)
    
    return df
    
# function to load or create leave planner
def load_or_update_leave_file(filepath, staff_list,leave_type):
    """
    Loads an existing weekly leave CSV OR creates/updates one
    with all weeks of the current year for all staff.

    Weeks are auto-generated based on today's date.
    """

    # -----------------------------------------
    # Auto-generate weekly start/end dates
    # -----------------------------------------
    today = date.today()
    year = today.year

    # First Monday of the year
    first_day = date(year, 1, 1)
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)

    # Last Monday of the year
    last_day = date(year, 12, 31)
    last_monday = last_day - timedelta(days=last_day.weekday())

    # Weekly list of Mondays
    weeks = pd.date_range(start=first_monday, end=last_monday, freq="W-MON")

    # Create full weekly structure
    def create_full_structure(staff):
        rows = []
        for s in staff:
            for w in weeks:
                rows.append({
                    "staff_member": s,
                    "week_commencing": w,
                    "week_number": w.isocalendar().week,
                    leave_type: 0
                })
        return pd.DataFrame(rows)

    # -----------------------------------------
    # CASE 1: File exists → load + update
    # -----------------------------------------
    if os.path.exists(filepath):
        existing = pd.read_csv(filepath, parse_dates=["week_commencing"])

        existing_staff = set(existing["staff_member"].unique())
        new_staff = set(staff_list) - existing_staff

        if new_staff:
            add_df = create_full_structure(new_staff)
            updated = pd.concat([existing, add_df], ignore_index=True)
            updated.to_csv(filepath, index=False)
            return updated

        return existing

    # -----------------------------------------
    # CASE 2: File does not exist → create new file
    # -----------------------------------------
    df = create_full_structure(staff_list)
    df[leave_type] = df[leave_type].round(decimals)
    df.to_csv(filepath, index=False)
    
    return df

# function to load or create leave planner
def load_or_update_planner_file(filepath, staff_list,activity_list):
    """
    Loads an existing weekly leave CSV OR creates/updates one
    with all weeks of the current year for all staff.

    Weeks are auto-generated based on today's date.
    """

    # -----------------------------------------
    # Auto-generate weekly start/end dates
    # -----------------------------------------
    today = date.today()
    year = today.year

    # First Monday of the year
    first_day = date(year, 1, 1)
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)

    # Last Monday of the year
    last_day = date(year, 12, 31)
    last_monday = last_day - timedelta(days=last_day.weekday())

    # Weekly list of Mondays
    planner_weeks = pd.date_range(start=first_monday, end=last_monday, freq="W-MON")

    # Create full weekly structure
    def create_planner_structure(staff, activity_list):
        rows = []

        for s in staff:
            for w in planner_weeks:
                row = {
                    "staff_member": s,
                    "week_commencing": w,
                    "week_number": w.isocalendar().week
                }

                # Add one column per activity type
                for act in activity_list:
                    row[act] = 0

                rows.append(row)

        return pd.DataFrame(rows)

    # -----------------------------------------
    # CASE 1: File exists → load + update
    # -----------------------------------------
    if os.path.exists(filepath):
        existing = pd.read_csv(filepath, parse_dates=["week_commencing"])

        existing_staff = set(existing["staff_member"].unique())
        new_staff = set(staff_list) - existing_staff

        if new_staff:
            add_df = create_planner_structure(new_staff,activity_list)
            updated = pd.concat([existing, add_df], ignore_index=True)
            updated.to_csv(filepath, index=False)
            return updated

        return existing

    # -----------------------------------------
    # CASE 2: File does not exist → create new file
    # -----------------------------------------
    df = create_planner_structure(staff_list,activity_list)
    df = df.round(decimals)
    df.to_csv(filepath, index=False)
    
    return df

def make_activity_chart(activity_calendar_df, activity_types):
    fig = go.Figure()

    # Add each activity type as its own stacked trace
    for act in activity_types:
        fig.add_trace(go.Bar(
            x=activity_calendar_df["week_commencing"],
            y=activity_calendar_df[act],
            name=act
        ))

    fig.update_layout(
        barmode="stack",
        title="Weekly Activity Breakdown",
        xaxis_title="Week Commencing",
        yaxis_title="Activity Amount",
        legend_title="Activity Type",
        hovermode="x unified"
    )

    return fig

def update_staff_list(staff_list_df, csv_path, new_staff=None, archive_staff=None):
    """
    new_staff: string of staff name to add
    archive_staff: string of staff name to set archive_flag = 1
    """
    
    # --- Add new staff ---
    if new_staff:
        if new_staff not in staff_list_df["staff_member"].values:
            staff_list_df.loc[len(staff_list_df)] = {
                "staff_member": new_staff,
                "archive_flag": 0
            }

    # --- Archive staff ---
    if archive_staff:
        staff_list_df.loc[
            staff_list_df["staff_member"] == archive_staff, "archive_flag"
        ] = 1

    # --- Save back to CSV ---
    staff_list_df.to_csv(csv_path, index=False)

    return staff_list_df

def update_programme_list(programme_list_df, csv_path, new_programme=None, archive_programme=None):
    
    # --- Add new staff ---
    if new_programme:
        if new_programme not in programme_list_df["programme_member"].values:
            programme_list_df.loc[len(programme_list_df)] = {
                "programme_member": new_programme,
                "archive_flag": 0
            }

    # --- Archive programme ---
    if archive_programme:
        programme_list_df.loc[
            programme_list_df["programme_member"] == archive_programme, "archive_flag"
        ] = 1

    # --- Save back to CSV ---
    programme_list_df.to_csv(csv_path, index=False)

    return programme_list_df

# def update_staff_list(staff_list_df, staff_name, action):
#     staff_name = staff_name.strip()

#     # If adding a new member
#     if action == "Add":
#         if staff_name in staff_list_df["staff_member"].values:
#             return False, "Staff member already exists."
        
#         new_row = {
#             "staff_member": staff_name,
#             "archive_flag": "N"
#         }
#         staff_list_df = pd.concat([staff_list_df, pd.DataFrame([new_row])], ignore_index=True)
#         return staff_list_df, f"Added new staff member: {staff_name}"

#     # If archiving a member
#     if action == "Archive":
#         if staff_name not in staff_list_df["staff_member"].values:
#             return False, "Staff member does not exist."

#         staff_list_df.loc[
#             staff_list_df["staff_member"] == staff_name, "archive_flag"
#         ] = "Y"
#         return staff_list_df, f"Archived staff member: {staff_name}"

#     # If unarchiving
#     if action == "Unarchive":
#         if staff_name not in staff_list_df["staff_member"].values:
#             return False, "Staff member does not exist."

#         staff_list_df.loc[
#             staff_list_df["staff_member"] == staff_name, "archive_flag"
#         ] = "N"
#         return staff_list_df, f"Unarchived staff member: {staff_name}"

#     return False, "Unknown action."