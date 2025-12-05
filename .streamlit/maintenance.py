import streamlit as st
import pandas as pd
import girft_planner_app as app
import planner_app as dat

st.title("System Maintenance")

st.subheader("Add or Remove Staff")

staff_list = dat.staff_list

staff_list_sorted = staff_list.sort_values(by="staff_member")

programme_list = dat.activity_list

programme_list_sorted = programme_list.sort_values(by="programme_categories")

with st.expander("🔧 Manage Staff List"):
    st.subheader("Add New Staff Member")
    new_staff = st.text_input("Input new staff member's name (Forename Surname) then click Add")

    # --- ADD STAFF MEMBER ---
    if st.button("➕ Add Staff Member"):
        updated = app.update_staff_list(
            staff_list_df=staff_list_sorted,      # use sorted df here
            csv_path="staff_list.csv",
            new_staff=new_staff
        )
        # sort again after update
        staff_list = updated.sort_values(by="staff_member")
        st.success(f"{new_staff} added successfully.")

    st.subheader("Archive Staff Member")

    # Always sort before showing the list to archive
    active_staff_sorted = staff_list.loc[
        staff_list["archive_flag"] == 0   
    ].sort_values(by="staff_member")["staff_member"]

    staff_to_archive = st.selectbox(
        "Select staff member to archive then click archive",
        active_staff_sorted
    )

    # --- ARCHIVE STAFF MEMBER ---
    if st.button("📦 Archive Selected Staff"):
        updated = app.update_staff_list(
            staff_list_df=staff_list,
            csv_path="staff_list.csv",
            archive_staff=staff_to_archive
        )
        # sort again after update
        staff_list = updated.sort_values(by="staff_member")
        st.success(f"{staff_to_archive} archived successfully.")

with st.expander("🔧 Manage Programme List"):
    st.subheader("Add New Programme")
    new_programme = st.text_input("Input new Programme Description then click Add")

    # --- ADD programme categories ---
    if st.button("➕ Add Programme"):
        updated = app.update_programme_list(
            programme_list_df=programme_list_sorted,      # use sorted df here
            csv_path="programme_categories.csv",
            new_programme=new_programme
        )
        # sort again after update
        programme_list = updated.sort_values(by="programme_categories")
        st.success(f"{new_programme} added successfully.")

    st.subheader("Archive Programme Category")

    # Always sort before showing the list to archive
    active_programme_sorted = programme_list.loc[
        programme_list["archive_flag"] == 0
    ].sort_values(by="programme_categories")["programme_categories"]

    programme_to_archive = st.selectbox(
        "Select programme categories to archive then click archive",
        active_programme_sorted
    )

    # --- ARCHIVE programme categories ---
    if st.button("📦 Archive Selected Programme"):
        updated = app.update_programme_list(
            programme_list_df=programme_list,
            csv_path="programme_categories.csv",
            archive_programme=programme_to_archive
        )
        # sort again after update
        programme_list = updated.sort_values(by="programme_categories")
        st.success(f"{programme_to_archive} archived successfully.")

