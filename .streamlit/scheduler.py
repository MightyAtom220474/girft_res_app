import streamlit as st
import pandas as pd
import planner_functions as pf
import data_store as ds
from datetime import date, timedelta

st.set_page_config(layout="wide")

def scheduler():

    staff_list = st.session_state.staff_list
    staff_names = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    
    st.title("📆 Scheduled Activity")
    st.subheader("⏱ Schedule Repeating Programme Activity for a Team Member")

    # ---------------------------
    # 1️⃣ Load active staff
    # ---------------------------
    staff_names = staff_list.loc[
        staff_list["archive_flag"] == 0, "staff_member"
    ].sort_values().tolist()

    selected_staff = st.selectbox(
        "Select Programme Team Member",
        staff_names,
        index=None,
        placeholder="Choose a staff member..."
    )

    # ---------------------------
    # 2️⃣ Load active programme categories (no archived)
    # ---------------------------
    active_programmes = programme_list.loc[
        programme_list["archive_flag"] == 0
    ].copy()

    programme_categories = sorted(
        active_programmes["programme_categories"].dropna().tolist()
    )

    selected_programme_category = st.selectbox(
        "Select Programme Category",
        programme_categories,
        index=None,
        placeholder="Choose a programme category..."
    )

    # ---------------------------
    # 3️⃣ Start week (week commencing)
    # ---------------------------
    week_commencing = st.date_input(
        "Select Start Week (Week Commencing / Monday)",
        help="This is the first Monday of the schedule.",
    )

    if week_commencing.weekday() != 0:
        st.warning("⚠️ The week commencing date should be a Monday.")

    # ---------------------------
    # 4️⃣ Number of weeks & hours per week
    # ---------------------------
    num_weeks = st.number_input(
        "Number of Weeks to Schedule",
        min_value=1,
        max_value=104,
        value=4,
        step=1,
        help="How many consecutive weeks to apply this activity for."
    )

    # 0 → 37.5 hours in 0.5 steps
    hour_values = [x * 0.5 for x in range(0, 76)]

    hours_per_week = st.selectbox(
        "Hours per Week",
        hour_values,
        index=hour_values.index(0.0),
        help="Scheduled hours per week for this programme category."
    )

    # ---------------------------
    # 5️⃣ Save button
    # ---------------------------
    if st.button("💾 Schedule Programme Activity"):
        if not selected_staff:
            st.error("Please select a staff member.")
        elif not selected_programme_category:
            st.error("Please select a programme category.")
        else:
            start_week = pd.to_datetime(week_commencing)

            # Loop over each week and update programme_activity in SQLite
            for week_offset in range(int(num_weeks)):
                this_week = start_week + pd.Timedelta(weeks=week_offset)

                # Build the activity_inputs dict expected by pf.save_programme_activity
                activity_inputs = {
                    selected_programme_category: float(hours_per_week)
                }

                pf.save_programme_activity(
                    selected_staff=selected_staff,
                    week_commencing=this_week,
                    activity_inputs=activity_inputs,
                )

            st.success(
                f"Scheduled {hours_per_week} hours/week of "
                f"**{selected_programme_category}** for **{selected_staff}** "
                f"over {num_weeks} week(s) starting "
                f"week commencing {start_week.date()}."
            )

            st.rerun()