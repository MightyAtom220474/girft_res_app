import streamlit as st
from streamlit import components
import pandas as pd
import os
import planner_functions as pf
import data_store as ds
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(layout="wide")

max_days = 5
steps = 50
# Calculate this week's Monday
today = date.today()
current_monday = today - timedelta(days=today.weekday())

def planner():
    
    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
        
    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df
    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df
    staff_names = st.session_state.staff_list
    programme_names = st.session_state.programme_list

    # # set up separate tabs for leave, on-site, and programme
    # tab1, tab2, tab3 = st.tabs(["Weekly Activity","Leave Record","Forward Planner"])

    st.title("📅 Activity Recording")
    st.subheader("✏️ Add or Edit Weekly Programme Activity for a Specific Team Member")

    # ---------------------------
    # 1️⃣ Load active staff
    # ---------------------------
    staff_names = staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"].sort_values().tolist()

    selected_staff = st.selectbox("Select Programme Team Member", staff_names, index=None)

    # display contracted hours and number of deployable hours
    
    if selected_staff:
        staff_info = staff_list.loc[staff_list["staff_member"] == selected_staff].head(1)

        if not staff_info.empty:
            hours_pw = float(staff_info.iloc[0].get("hours_pw", 0) or 0)
            deploy_ratio = float(staff_info.iloc[0].get("deploy_ratio", 0) or 0)
            deployable_hours = hours_pw * deploy_ratio

            c1, c2 = st.columns(2)
            c1.metric("Contracted hours (per week)", f"{hours_pw:.1f}")
            c2.metric("Deployable hours (per week)", f"{deployable_hours:.1f}")
        else:
            st.info("No staff contract info found for this staff member.")

    # ---------------------------
    # 2️⃣ Week commencing
    # ---------------------------
    week_commencing = st.date_input(
        "Select Week Commencing (Monday)",
        value=current_monday,
        help="Choose the Monday of the week you want to enter activity for"
    )

    if week_commencing.weekday() != 0:
        st.warning("⚠️ The week commencing date must be a Monday.")

    # ---------------------------
    # 3️⃣ Programme group filter
    # ---------------------------
    # Only non-archived programmes
    active_programmes = programme_list.loc[programme_list["archive_flag"] == 0].copy()

    programme_groups = ["All"] + sorted(active_programmes["programme_group"].dropna().unique().tolist())
    selected_group = st.selectbox("Select Programme Group", programme_groups, index=0)

    if selected_group == "All":
        programmes_filtered = active_programmes
    else:
        programmes_filtered = active_programmes.loc[active_programmes["programme_group"] == selected_group]

    # Programme categories to display
    programme_categories_filtered = programmes_filtered["programme_categories"].tolist()

    # ---------------------------
    # Determine activity rows for selected staff & week
    # ---------------------------
    mask = (
        (programme_calendar_df["staff_member"] == selected_staff) &
        (programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing)) &
        (programme_calendar_df["programme_category"].isin(programme_categories_filtered))
    )

    # Filter the relevant rows
    staff_activities = programme_calendar_df.loc[mask].copy()

    # If no activity exists yet, create a default row with zeros
    if staff_activities.empty:
        staff_activities = pd.DataFrame({
            "staff_member": [selected_staff]*len(programme_categories_filtered),
            "week_commencing": [pd.to_datetime(week_commencing)]*len(programme_categories_filtered),
            "week_number": [pd.to_datetime(week_commencing).isocalendar()[1]]*len(programme_categories_filtered),
            "programme_category": programme_categories_filtered,
            "activity_value": [0.0]*len(programme_categories_filtered)
        })

    # ---------------------------
    # 6️⃣ Build selectboxes for each activity
    # ---------------------------
    st.write(f"### Editing Programme Activity for: **{selected_staff}**")
    st.write(f"#### Week Commencing: **{week_commencing}**")

    mask = (
        (programme_calendar_df["staff_member"] == selected_staff) &
        (programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing))
    )

    if mask.any():
        staff_row = programme_calendar_df.loc[mask].iloc[0]
    else:
        staff_row = pd.Series({col: 0.0 for col in programme_categories_filtered})

    # 0 → 37.5 in 0.5 steps
    hour_values = [x * 0.5 for x in range(0, 76)]

    activity_inputs = {}

    for col in programme_categories_filtered:
        default_value = float(staff_row[col]) if col in staff_row else 0.0
        pretty_name = col.replace("_", " ").title()

        activity_inputs[col] = st.selectbox(
            pretty_name,
            hour_values,
            index=hour_values.index(default_value) if default_value in hour_values else 0
        )

    # ---------------------------
    # 7️⃣ Save button
    # ---------------------------
    if st.button("💾 Save Programme Activity Changes"):
        pf.save_programme_activity(
            selected_staff=selected_staff,
            week_commencing=week_commencing,
            activity_inputs=activity_inputs
        )

        st.success(
            f"Programme activity saved for {selected_staff} "
            f"week commencing {pd.to_datetime(week_commencing).date()}"
        )

        st.rerun()   # ← force immediate refresh