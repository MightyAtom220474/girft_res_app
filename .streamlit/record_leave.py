import streamlit as st
import pandas as pd
import planner_functions as pf
import data_store as ds
from data_store import DB_PATH
ds.handle_trigger_reload() # force reloading of any saved data
from datetime import date, timedelta
import time
import sqlite3

max_days = 5
steps = 50
# Calculate this week's Monday
today = date.today()
current_monday = today - timedelta(days=today.weekday())

def refresh_leave_calendar():
    """Reload only the leave calendar from the database into session state."""

    with sqlite3.connect(DB_PATH) as conn:
        st.session_state.leave_calendar_df = pd.read_sql("SELECT * FROM leave_calendar", conn)
    # Re‑parse week_commencing dates (reuse your helper if available)
    st.session_state.leave_calendar_df["week_commencing"] = pd.to_datetime(
        st.session_state.leave_calendar_df["week_commencing"], errors="coerce"
    )

# page for blocking out leave days - annual leave and sickness
def leave():

    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
        
    staff_list = st.session_state.staff_list
    staff_names = st.session_state.staff_list

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("✈️ Leave Record")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        #st.write("Email: info@gettingitrightfirsttime.co.uk")
    
    st.divider()
    
    # ------------------------------------------------
    # Select staff to edit
    # ------------------------------------------------
    st.subheader("✏️ Add or Edit Leave for a Team Member")

    with st.expander("Click to See User Guidance"):
        st.markdown("""Please record all types of leave here (i.e. annual leave
                    , sickness leave, carers leave, parental leave, special 
                    leave, jury service, volunteering leave, 
                    training leave etc.).""")

    # ------------------------------------------------
    # Select Staff Member
    # ------------------------------------------------
    staff_names = (
        st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
        .sort_values()
        .tolist()
    )

    # Find the staff_member corresponding to the logged-in username
    logged_in_user = st.session_state.get("username", None)
    default_index = 0  # fallback index
    if logged_in_user:
        row = staff_list.loc[staff_list["username"] == logged_in_user]
        if not row.empty:
            staff_name = row["staff_member"].iloc[0]
            if staff_name in staff_names:
                default_index = staff_names.index(staff_name)

    selected_staff = st.selectbox("Select Leave Team Member", staff_names, index=default_index)

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
        # Show success message temporarily
        success_box = st.empty()
        success_box.success(
            f"Leave saved for {selected_staff} "
            f"week commencing {pd.to_datetime(week_commencing).date()}"
        )
        time.sleep(3)
        success_box.empty()
        # Flag the app to reload only the leave data, not the entire store
        st.session_state["trigger_reload"] = "leave"
        st.rerun()