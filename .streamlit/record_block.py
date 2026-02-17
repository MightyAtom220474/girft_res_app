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

# page for blocking out days in onsite calendar
def block():

    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
        
    staff_list = st.session_state.staff_list
    staff_names = st.session_state.staff_list

    st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)

    st.title("📅 Forward Planner")

    st.write("Please book out here any days where you are likely to be"
                " unavailable for other work due to full-day commitments. "
                "This could include: team away days; Further Faster visits"
                "; Men-SAT summits or Maturity Tool deployments;"
                " conferences; formal training or learning; or any other "
                "on-site activity (e.g. Provider Improvement Programme "
                "on-site work).")

    # ------------------------------------------------
    # Load staff names (active only)
    # ------------------------------------------------
    staff_names = (
        st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
        .sort_values()
        .tolist()
    )

    # ------------------------------------------------
    # Select Staff Member to Edit
    # ------------------------------------------------
    st.subheader("✏️ Add or Edit Block Booking days for a Specific Team Member")

    selected_staff_os = st.selectbox("Select Block Booking Team Member", staff_names, index=None)

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
        [x for x in range(0, 5)],    # 0 → 5 in 1 day steps
        help="Select number of whole days that week (max 5)"
    )

    # ------------------------------------------------
    # Save Button
    # ------------------------------------------------
    if st.button("💾 Save Block Booking Changes"):
        pf.save_on_site(
            staff_member=selected_staff_os,
            week_commencing=week_commencing_os,
            on_site_days=on_site_days
        )

        st.success(
            f"Block Booking saved for {selected_staff_os} "
            f"week commencing {pd.to_datetime(week_commencing_os).date()}, {on_site_days}"
        )

        st.rerun()   # ← force immediate refresh