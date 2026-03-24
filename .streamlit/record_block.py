import streamlit as st
import pandas as pd
import planner_functions as pf
import data_store as ds
ds.handle_trigger_reload() # force reloading of any saved data
from datetime import date, timedelta
import time

st.set_page_config(layout="wide")

max_days = 5
steps = 50
# Calculate this week's Monday
today = date.today()
current_monday = today - timedelta(days=today.weekday())

# page for blocking out days in onsite calendar
def block():

    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
    
    staff_list = st.session_state.staff_list
    staff_names = st.session_state.staff_list
    programme_names = st.session_state.programme_names

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("🗓️ Forward Planner")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        st.write("Email: info@gettingitrightfirsttime.co.uk")

    st.divider()

    # ------------------------------------------------
    # Load staff names (active only)
    # ------------------------------------------------
    staff_names = (
        st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
        .sort_values()
        .tolist()
    )
    
    # Add custom entries manually so can book out for other reasons
    custom_programmes = ["Team Away Day", "Team Meeting"]
    # Merge them and remove duplicates (if any)
    programme_names = sorted(list(set(programme_names + custom_programmes)))

    # Find the staff_member corresponding to the logged-in username
    logged_in_user = st.session_state.get("username", None)
    default_index = 0  # fallback index
    if logged_in_user:
        row = staff_list.loc[staff_list["username"] == logged_in_user]
        if not row.empty:
            staff_name = row["staff_member"].iloc[0]
            if staff_name in staff_names:
                default_index = staff_names.index(staff_name)
    
    # ------------------------------------------------
    # Select Staff Member to Edit
    # ------------------------------------------------
    st.subheader("✏️ Add or Edit Block Booking days for a Specific Team Member")

    with st.expander("Click to See User Guidance"):
        st.markdown("""Please book here any days where you are likely to be 
                    unavailable for other work due to full-day commitments. 
                    This could include: Team Away Days; Further Faster visits; 
                    Men-SAT summits or Maturity Tool deployments; 
                    conferences; formal training; or any other on-site activity
                     (e.g. Provider Improvement Programme on-site work).""")

    selected_staff_os = st.selectbox(
        "Select Block Booking Team Member",
        staff_names,
        index=default_index)

    selected_prog_os = st.selectbox("Select Work Programme or GIRFT Team Event", programme_names, index=None)

    # ------------------------------------------------
    # Select Week Commencing (Monday)
    # ------------------------------------------------
    week_commencing_os = st.date_input(
        "Select Week Commencing (Monday)",
        value=current_monday,
        help="Choose the Monday of the week the Block Booking applies to"
    )

    # Make sure the date is a Monday
    if week_commencing_os.weekday() != 0:
        st.warning("⚠️ The week commencing date must be a Monday.")

    # ------------------------------------------------
    # Days On Site Input (0 - 5 in whole day increments)
    # ------------------------------------------------
    on_site_days = st.selectbox(
        f"Number of days to be Block Booked out for w/c {week_commencing_os}",
        [x for x in range(1, 6)],    # 1 → 5 in 1 day steps
        help="Select number of whole days that week (max 5)"
    )

    # ------------------------------------------------
    # Save Button
    # ------------------------------------------------
    if st.button("💾 Save Block Booking Changes"):
        pf.save_on_site(
            staff_member=selected_staff_os,
            programme_category=selected_prog_os,
            week_commencing=week_commencing_os,
            on_site_days=on_site_days
        )
        # Create a placeholder for the success message
        success_box = st.empty()
        success_box.success(
            f"Block Booking saved for {selected_staff_os} and programme {selected_prog_os} "
            f"week commencing {pd.to_datetime(week_commencing_os).date()}, {on_site_days}"
        )
        # Keep it visible for 3 seconds
        time.sleep(3)
        success_box.empty()
        st.session_state["trigger_reload"] = "onsite"

        st.rerun()   # ← force immediate refresh