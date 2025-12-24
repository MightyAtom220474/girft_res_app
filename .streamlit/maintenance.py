import streamlit as st
import pandas as pd
from planner_functions import update_staff_list, update_programme_list
import data_store as ds
import sqlite3

DB_PATH = "girft_capacity_planner.db"

def maintenance():

    ds.load_or_refresh_all()

    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df
    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df
    staff_names = st.session_state.staff_list
    programme_names = st.session_state.programme_list

    st.title("System Maintenance")

    st.subheader("Add or Remove Staff")

    #staff_list = staff_list

    #staff_list_sorted = staff_list.sort_values(by="staff_member")

    #programme_list = programme_list

    programme_list_sorted = programme_list.sort_values(by="programme_categories")

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

        username_input = st.text_input("Staff member User Name (.net email address if available)")

        access_level = st.selectbox(
                                    "User Access Level",
                                    options=["admin", "user", "viewer"],
                                    key="access_level"
                                    )

        if st.button("➕ Add Staff Member"):
            update_staff_list(
                new_staff=new_staff,
                job_role=job_role,
                hours_pw=hours_pw,
                leave_allowance_days=leave_allowance_days,
                is_deployable=is_deployable_flag,
                deploy_ratio=deploy_ratio,
                username=username_input,
                password=ds.default_password,
                user_access=access_level
            )

            # Reload fresh data from the database
            #staff_list = ds.load_staff_list().sort_values(by="staff_member")

            st.success(f"{new_staff} added successfully.")

        # -----------------------------------------------------------------
        # ARCHIVE SECTION
        # -----------------------------------------------------------------
        st.subheader("Archive Staff Member")

        # ---------------------------
        # Load active staff from DB
        # ---------------------------
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT staff_member
                FROM staff_list
                WHERE archive_flag = 0
                ORDER BY staff_member
                """
            )

        archive_staff = [row[0] for row in cursor.fetchall()]

        if archive_staff:
            staff_to_archive = st.selectbox(
                "Select staff member to archive",
                archive_staff
            )

            # ---------------------------
            # ARCHIVE STAFF MEMBER
            # ---------------------------
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                if st.button("Archive Selected Staff"):
                    cursor.execute(
                        """
                        UPDATE staff_list
                        SET archive_flag = 1
                        WHERE staff_member = ?
                        """,
                        (staff_to_archive,)
                    )
                    conn.commit()

                    st.success(f"{staff_to_archive} archived successfully.")

                    # Optional: refresh cached data
                    ds.load_or_refresh_all()

        else:
            st.info("No active staff to archive.")

            # Optional: refresh cached data
            ds.load_or_refresh_all()

            st.rerun()   # ← force immediate refresh
        
        # -----------------------------------------------------------------
        # RESTORE ARCHIVED STAFF
        # -----------------------------------------------------------------
        st.subheader("Restore Archived Staff Member")

        # ---------------------------
        # Load archived staff from DB
        # ---------------------------
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT staff_member
                FROM staff_list
                WHERE archive_flag = 1
                ORDER BY staff_member
                """
            )

        archived_staff = [row[0] for row in cursor.fetchall()]

        if archived_staff:
            staff_to_restore = st.selectbox(
                "Select archived staff member to restore",
                archived_staff
            )

            # ---------------------------
            # RESTORE STAFF MEMBER
            # ---------------------------
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                if st.button("Restore Selected Staff"):
                    cursor.execute(
                        """
                        UPDATE staff_list
                        SET archive_flag = 0
                        WHERE staff_member = ?
                        """,
                        (staff_to_restore,)
                    )
                    conn.commit()

                    st.success(f"{staff_to_restore} restored successfully.")

                    # Optional: refresh cached data
                    ds.load_or_refresh_all()

                    st.rerun()   # ← force immediate refresh

        else:
            st.info("No archived staff to restore.")


    with st.expander("🔧 Manage Programme List"):
        st.subheader("Add New Programme Category")

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
            update_programme_list(
                new_programme=new_programme,
                programme_type=programme_type,
                programme_group=programme_group
            )

            programme_list = programme_list.sort_values(by="programme_categories")

            st.success(f"{new_programme} added successfully.")

            st.rerun()   # ← force immediate refresh

        # ----------------------------
        # Archive existing programmes
        # ----------------------------

        st.subheader("Archive Programme Category")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                    """
                    SELECT programme_categories
                    FROM programme_categories
                    WHERE archive_flag = 0
                    ORDER BY programme_categories
                    """
                )
            
            active_programmes = [row[0] for row in cursor.fetchall()]

            programme_to_archive = st.selectbox(
                "Select programme to archive",
                active_programmes
            )

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if st.button("Archive Selected Programme"):
                cursor.execute(
                    """
                    UPDATE programme_categories
                    SET archive_flag = 1
                    WHERE programme_categories = ?
                    """,
                    (programme_to_archive,)
                )
                conn.commit()

                st.success(f"{programme_to_archive} archived successfully.")

                # Optional: refresh cached data
                ds.load_or_refresh_all()

                st.rerun()   # ← force immediate refresh

        # ----------------------------
        # Archive existing programmes
        # ----------------------------

        st.subheader("Restore Programme Category")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                    """
                    SELECT programme_categories
                    FROM programme_categories
                    WHERE archive_flag = 1
                    ORDER BY programme_categories
                    """
                )
            
            archived_programmes = [row[0] for row in cursor.fetchall()]

            programme_to_restore = st.selectbox(
                "Select programme to restore",
                archived_programmes
            )

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if st.button("Restore Selected Programme"):
                cursor.execute(
                    """
                    UPDATE programme_categories
                    SET archive_flag = 0
                    WHERE programme_categories = ?
                    """,
                    (programme_to_restore,)
                )
                conn.commit()

                st.success(f"{programme_to_restore} restored successfully.")

                # Optional: refresh cached data
                ds.load_or_refresh_all()

                st.rerun()   # ← force immediate refresh    




