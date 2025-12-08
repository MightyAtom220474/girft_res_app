import streamlit as st
import pandas as pd
from planner_functions import update_staff_list, update_programme_list
import data_store as ds


def maintenance():

    st.title("System Maintenance")

    st.subheader("Add or Remove Staff")

    #staff_list = staff_list

    staff_list_sorted = ds.staff_list.sort_values(by="staff_member")

    #programme_list = programme_list

    programme_list_sorted = ds.programme_list.sort_values(by="programme_categories")

    with st.expander("🔧 Manage Staff List"):
        st.subheader("Add New Staff Member")

        new_staff = st.text_input("Staff member name (Forename Surname)")

        job_role = st.text_input("Job Role")

        hours_pw = st.selectbox(
            "Number of Contracted Hours per Week",
            [i * 0.5 for i in range(0, 76)],  # 0 → 37.5 in steps of 0.5
            format_func=lambda x: f"{x:.1f}"
        )

        leave_allowance_days = st.selectbox(
            "Leave Allowance (days)",
            list(range(0, 36))  # up to 35
        )

        is_deployable = st.radio(
            "Is Deployable?",
            ["Yes", "No"]
        )
        is_deployable_flag = 1 if is_deployable == "Yes" else 0

        deploy_ratio = st.selectbox(
            "Deployment Ratio",
            [i * 0.1 for i in range(0, 11)],  # 0 → 1 in 0.1 steps
            format_func=lambda x: f"{x:.1f}"
        )

        # --- ADD STAFF MEMBER ---
        if st.button("➕ Add Staff Member"):
            updated = update_staff_list(
                staff_list_df=staff_list_sorted,      
                csv_path="staff_list.csv",
                new_staff=new_staff,
                job_role=job_role,
                hours_pw=hours_pw,
                leave_allowance_days=leave_allowance_days,
                is_deployable=is_deployable_flag,
                deploy_ratio=deploy_ratio
            )

            # Refresh list so new staff becomes immediately available to archive
            ds.staff_list = updated.sort_values(by="staff_member")

            st.success(f"{new_staff} added successfully.")

        # -----------------------------------------------------------------
        # ARCHIVE SECTION
        # -----------------------------------------------------------------
        st.subheader("Archive Staff Member")

        active_staff_sorted = ds.staff_list.loc[
            ds.staff_list["archive_flag"] == 0
        ].sort_values(by="staff_member")["staff_member"]

        staff_to_archive = st.selectbox(
            "Select staff member to archive",
            active_staff_sorted
        )

        # --- ARCHIVE STAFF MEMBER ---
        if st.button("📦 Archive Selected Staff"):
            updated = update_staff_list(
                staff_list_df=ds.staff_list,
                csv_path="staff_list.csv",
                archive_staff=staff_to_archive
            )

            ds.staff_list = updated.sort_values(by="staff_member")
            st.success(f"{staff_to_archive} archived successfully.")

    with st.expander("🔧 Manage Programme List"):
        st.subheader("Add New Programme")

        # ----------------------------
        # Inputs for new programme
        # ----------------------------
        new_programme = st.text_input("Programme Category (e.g., Intensive Support)")

        programme_type = st.radio(
            "Programme Type",
            ["Deployable", "Non-Deployable"]
        )

        programme_group_options = sorted([
            "CYP",
            "Inpatient and Rehab",
            "Intensive Support",
            "Crisis, Urgent and Emergency Care",
            "Universal Offer",
            "General"
        ])

        programme_group = st.selectbox(
            "Programme Group",
            programme_group_options
        )

        # --- ADD PROGRAMME ---
        if st.button("➕ Add Programme"):
            ds.programme_list = update_programme_list(
                programme_list_df=programme_list_sorted,          # <-- use live df, NOT sorted copy
                csv_path="programme_categories.csv",
                new_programme=new_programme,
                programme_type=programme_type,
                programme_group=programme_group
            )

            ds.programme_list = ds.programme_list.sort_values(by="programme_categories")

            st.success(f"{new_programme} added successfully.")

        # ----------------------------
        # Archive existing programmes
        # ----------------------------
        st.subheader("Archive Programme Category")

        active_programme_sorted = (
            ds.programme_list.loc[ds.programme_list["archive_flag"] == 0]
            .sort_values(by="programme_categories")["programme_categories"]
        )

        programme_to_archive = st.selectbox(
            "Select programme to archive",
            active_programme_sorted
        )

        if st.button("📦 Archive Selected Programme"):
            ds.programme_list = update_programme_list(
                programme_list_df=ds.programme_list,
                csv_path="programme_categories.csv",
                archive_programme=programme_to_archive
            )

            ds.programme_list = ds.programme_list.sort_values(by="programme_categories")

            st.success(f"{programme_to_archive} archived successfully.")




