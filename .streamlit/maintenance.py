import streamlit as st
import pandas as pd
import girft_planner_app as app

st.title("System Maintenance")

st.subheader("Add or Remove Staff")

with st.expander("🔧 Manage Staff List"):
    st.subheader("Add New Staff Member")
    new_staff = st.text_input("New staff member name")

    if st.button("➕ Add Staff Member"):
        staff_list = app.update_staff_list(
            staff_list_df=app.staff_list,
            csv_path="staff_list.csv",
            new_staff=new_staff
        )
        st.success(f"{new_staff} added successfully.")

    st.subheader("Archive Staff Member")
    staff_to_archive = st.selectbox(
        "Select staff to archive",
        staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
    )

    if st.button("📦 Archive Selected Staff"):
        staff_list = app.update_staff_list(
            staff_list_df=staff_list,
            csv_path="staff_list.csv",
            archive_staff=staff_to_archive
        )
        st.success(f"{staff_to_archive} archived successfully.")

