import streamlit as st
import pandas as pd
import planner_functions as pf
import data_store as ds
from datetime import date, timedelta

st.set_page_config(layout="wide")

max_days = 5
steps = 50
# Calculate this week's Monday
today = date.today()
current_monday = today - timedelta(days=today.weekday())

# page for blocking out leave days - annual leave and sickness
def leave():

    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
        
    staff_list = st.session_state.staff_list
    staff_names = st.session_state.staff_list

    st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)

    st.title("📅 Leave Record")
    
    # ------------------------------------------------
    # Select staff to edit
    # ------------------------------------------------
    st.subheader("✏️ Add or Edit Leave for a Team Member")

    # ------------------------------------------------
    # Select Staff Member
    # ------------------------------------------------
    staff_names = (
        st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
        .sort_values()
        .tolist()
    )

    selected_staff = st.selectbox("Select Leave Team Member", staff_names, index=None)

    # ------------------------------------------------
    # Pick Week Commencing (Monday only)
    # ------------------------------------------------
    week_commencing = st.date_input(
        "Select Week Commencing (Monday)",
        value=current_monday,
        help="Choose the Monday of the week the leave applies to"
    )

    # Optional validation (ensure it's a Monday)
    if week_commencing.weekday() != 0:
        st.warning("⚠️ The week commencing date must be a Monday.")

    # ------------------------------------------------
    # Leave Days Input (0.5 to 5 in 0.5 increments)
    # ------------------------------------------------
    days_leave = st.selectbox(
        "Number of Leave Days",
        [x * 0.5 for x in range(0, 11)],  # 0, 0.5, ..., 5
        help="Select whole or half days (max 5)"
    )

    # ------------------------------------------------
    # Save Button
    # ------------------------------------------------
    if st.button("💾 Save Leave Changes"):
        pf.save_annual_leave(
            staff_member=selected_staff,
            week_commencing=week_commencing,
            days_leave=days_leave
        )

        st.success(
            f"Leave saved for {selected_staff} "
            f"week commencing {pd.to_datetime(week_commencing).date()}"
        )

        st.rerun()   # ← force immediate refresh