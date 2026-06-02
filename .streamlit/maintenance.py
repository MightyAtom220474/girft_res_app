import streamlit as st
import pandas as pd
from planner_functions import update_staff_list, update_programme_list
from db import execute, query_df
import data_store as ds
import planner_functions as pf
import io
from datetime import datetime
import zipfile
from werkzeug.security import generate_password_hash


def maintenance():

    ds.load_or_refresh_all()

    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("🛠️ System Maintenance")
    with col2:
        st.image(
            "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg",
            width=300
        )

    st.divider()
    st.subheader("Add or Remove Staff")

    programme_list_sorted = programme_list.sort_values(by="programme_category")

    # ============================================================
    # STAFF MANAGEMENT
    # ============================================================
    with st.expander("👥 Manage Staff List"):

        st.subheader("➕ Add New Staff Member")

        new_staff = st.text_input("Staff member name (Forename Surname)")
        job_role = st.text_input("Job Role")

        hours_pw = st.selectbox(
            "Number of Contracted Hours per Week",
            [i * 0.5 for i in range(0, 76)],
            format_func=lambda x: f"{x:.1f}"
        )

        leave_allowance_days = st.selectbox(
            "Leave Allowance (days)",
            list(range(0, 36))
        )

        is_deployable = st.radio("Is Deployable?", ["Yes", "No"])
        is_deployable_flag = 1 if is_deployable == "Yes" else 0

        deploy_ratio = st.selectbox(
            "Deployment Ratio",
            [i * 0.1 for i in range(0, 11)],
            format_func=lambda x: f"{x:.1f}"
        )

        active_programmes = (
            programme_list.loc[
                programme_list["archive_flag"] == 0,
                "programme_category"
            ]
            .dropna()
            .sort_values()
            .tolist()
        )

        default_programme = st.selectbox(
            "Default Programme",
            options=["None"] + active_programmes,
            index=0
        )

        if default_programme == "None":
            default_programme = None

        username_input = st.text_input("Username (.net email)")

        access_level = st.selectbox(
            "User Access Level",
            options=["admin", "user", "viewer"],
        )

        if st.button("➕ Add Staff Member"):

            update_staff_list(
                new_staff=new_staff,
                job_role=job_role,
                hours_pw=hours_pw,
                leave_allowance_days=leave_allowance_days,
                is_deployable=is_deployable_flag,
                deploy_ratio=deploy_ratio,
                default_programme=default_programme,
                username=username_input,
                password=ds.default_password,
                user_access=access_level
            )

            st.success(f"{new_staff} added successfully.")
            ds.load_or_refresh_all()

        # ============================================================
        # ARCHIVE STAFF
        # ============================================================
        st.subheader("🗑️ Archive Staff Member")

        archive_staff_df = query_df("""
            SELECT staff_member
            FROM staff_list
            WHERE archive_flag = 0
            ORDER BY staff_member
        """)

        archive_staff = archive_staff_df["staff_member"].tolist()

        staff_to_archive = st.selectbox(
            "Select staff member to archive",
            archive_staff if archive_staff else [],
            index=None
        )

        if st.button("Archive Selected Staff") and staff_to_archive:

            execute("""
                UPDATE staff_list
                SET archive_flag = 1
                WHERE staff_member = %s
            """, (staff_to_archive,))

            st.success("Archived successfully")
            ds.load_or_refresh_all()
            st.rerun()

        # ============================================================
        # RESTORE STAFF
        # ============================================================
        st.subheader("♻️ Restore Staff Member")

        archived_df = query_df("""
            SELECT staff_member
            FROM staff_list
            WHERE archive_flag = 1
            ORDER BY staff_member
        """)

        archived_staff = archived_df["staff_member"].tolist()

        staff_to_restore = st.selectbox(
            "Select archived staff",
            archived_staff if archived_staff else [],
            index=None
        )

        if st.button("Restore Selected Staff") and staff_to_restore:

            execute("""
                UPDATE staff_list
                SET archive_flag = 0
                WHERE staff_member = %s
            """, (staff_to_restore,))

            st.success("Restored successfully")
            ds.load_or_refresh_all()
            st.rerun()

        # ============================================================
        # RESET INDIVIDUAL PASSWORD
        # ============================================================
        st.subheader("🔐 Reset Individual Password")

        staff_df = query_df("""
            SELECT staff_member FROM staff_list ORDER BY staff_member
        """)

        staff_members = staff_df["staff_member"].tolist()

        staff_to_reset = st.selectbox(
            "Select staff member",
            staff_members,
            index=None
        )

        temp_pw = st.text_input("Temporary password", "Temporary123!")

        if st.button("Reset Password") and staff_to_reset:

            row = query_df("""
                SELECT username
                FROM staff_list
                WHERE staff_member = %s
            """, (staff_to_reset,))

            if row.empty or not row.iloc[0, 0]:
                st.error("No username found")
            else:
                username = row.iloc[0, 0]
                hashed = generate_password_hash(temp_pw)

                execute("""
                    UPDATE staff_list
                    SET password = %s,
                        must_change_password = 1
                    WHERE username = %s
                """, (hashed, username))

                st.success("Password reset")
                ds.load_or_refresh_all()
                st.rerun()

        # ============================================================
        # RESET ALL PASSWORDS
        # ============================================================
        st.subheader("⚠️ Reset ALL Passwords")

        temp_pw_all = st.text_input("Temp password all users", "Temporary123!")
        confirm = st.text_input("Type RESET ALL")

        if st.button("Reset ALL"):
            if confirm.strip().upper() == "RESET ALL":

                users = query_df("""
                    SELECT username
                    FROM staff_list
                    WHERE username IS NOT NULL
                """)

                for username in users["username"]:
                    hashed = generate_password_hash(temp_pw_all)

                    execute("""
                        UPDATE staff_list
                        SET password = %s,
                            must_change_password = 1
                        WHERE username = %s
                    """, (hashed, username))

                st.success("All passwords reset securely")
                ds.load_or_refresh_all()
                st.rerun()

        # ============================================================
        # ACCESS LEVEL
        # ============================================================
        st.subheader("🔐 Change Access Level")

        available_df = query_df("""
            SELECT staff_member
            FROM staff_list
            WHERE archive_flag = 0
        """)

        available_staff = available_df["staff_member"].tolist()

        staff_to_change = st.selectbox(
            "Select staff",
            available_staff if available_staff else [],
            index=None
        )

        access = st.selectbox("Access", ["admin", "user", "viewer"])

        if st.button("Update Access") and staff_to_change:

            execute("""
                UPDATE staff_list
                SET access_level = %s
                WHERE staff_member = %s
            """, (access, staff_to_change))

            st.success("Updated")
            ds.load_or_refresh_all()
            st.rerun()

    # ============================================================
    # EXPORT DATABASE
    # ============================================================
    st.divider()
    st.subheader("📤 Export Database")

    if st.button("Export All"):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_buffer = io.BytesIO()

        tables = [
            "staff_list",
            "programme_categories",
            "programme_activity",
            "leave_calendar",
            "on_site_calendar"
        ]

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for table in tables:
                df = query_df(f"SELECT * FROM {table}")

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)

                zip_file.writestr(
                    f"{table}_{timestamp}.csv",
                    csv_buffer.getvalue()
                )

        zip_buffer.seek(0)

        st.download_button(
            "Download Export",
            zip_buffer,
            file_name=f"export_{timestamp}.zip",
            mime="application/zip"
        )