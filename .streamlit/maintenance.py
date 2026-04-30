import streamlit as st
import pandas as pd
from planner_functions import update_staff_list, update_programme_list
import data_store as ds
import sqlite3
import planner_functions as pf
import io
from datetime import datetime
import zipfile

DB_PATH = "girft_capacity_planner.db"


def maintenance():

    ds.load_or_refresh_all()

    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df
    leave_calendar_df = st.session_state.leave_calendar_df

    st.set_page_config(layout="wide")

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

    programme_list_sorted = programme_list.sort_values(by="programme_categories")

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

        # ------------------------------------------------------------
        # DEFAULT PROGRAMME (SAFE HANDLING)
        # ------------------------------------------------------------
        active_programmes = (
            programme_list.loc[
                programme_list["archive_flag"] == 0,
                "programme_categories"
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

        # Convert "None" → actual None for DB
        if default_programme == "None":
            default_programme = None

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
                default_programme=default_programme,
                username=username_input,
                password=ds.default_password,
                user_access=access_level
            )

            st.success(f"{new_staff} added successfully.")
            ds.load_or_refresh_all()

        # ================================
        # ARCHIVE STAFF
        # ================================
        st.subheader("🗑️ Archive Staff Member")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT staff_member
                FROM staff_list
                WHERE archive_flag = 0
                ORDER BY staff_member
            """)
            archive_staff = [row[0] for row in cursor.fetchall()]

        if archive_staff:
            staff_to_archive = st.selectbox(
                "Select staff member to archive",
                archive_staff,
                index=None
            )

            if st.button("Archive Selected Staff"):
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE staff_list
                        SET archive_flag = 1
                        WHERE staff_member = ?
                    """, (staff_to_archive,))
                    conn.commit()

                st.success(f"{staff_to_archive} archived successfully.")
                ds.load_or_refresh_all()

        else:
            st.info("No active staff to archive.")

        # ================================
        # RESTORE STAFF
        # ================================
        st.subheader("♻️ Restore Archived Staff Member")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT staff_member
                FROM staff_list
                WHERE archive_flag = 1
                ORDER BY staff_member
            """)
            archived_staff = [row[0] for row in cursor.fetchall()]

        if archived_staff:
            staff_to_restore = st.selectbox(
                "Select archived staff member to restore",
                archived_staff,
                index=None
            )

            if st.button("Restore Selected Staff"):
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE staff_list
                        SET archive_flag = 0
                        WHERE staff_member = ?
                    """, (staff_to_restore,))
                    conn.commit()

                st.success(f"{staff_to_restore} restored successfully.")
                ds.load_or_refresh_all()
                st.rerun()

        else:
            st.info("No archived staff to restore.")

    # ============================================================
    # PROGRAMME SECTION (UNCHANGED)
    # ============================================================
    with st.expander("🔧 Manage Programme List"):

        st.subheader("Add New Programme Category")

        new_programme = st.text_input("Programme Category")
        programme_type = st.radio("Programme Type", ["Deployable", "Non-Deployable"])

        programme_group_options = sorted(
            programme_list.loc[
                programme_list["archive_flag"] == 0,
                "programme_group"
            ].dropna().unique().tolist()
        )

        programme_group_options_with_new = programme_group_options + ["➕ Add new group"]

        selected_group = st.selectbox(
            "Programme Group",
            programme_group_options_with_new
        )

        if selected_group == "➕ Add new group":
            programme_group = st.text_input("Enter new Programme Group")
        else:
            programme_group = selected_group

        if st.button("➕ Add Programme"):
            update_programme_list(
                new_programme=new_programme,
                programme_type=programme_type,
                programme_group=programme_group
            )
            ds.load_or_refresh_all()
            st.success(f"{new_programme} added successfully.")
            st.rerun()

    # ============================================================
    # DATA CHECK
    # ============================================================
    with st.expander("🚨 Data Entry Checklist"):

        st.subheader("Status for Previous Week")

        df_flags = pf.get_inactive_staff_with_reasons(
            staff_list,
            programme_calendar_df,
            leave_calendar_df
        )

        pf.render_followup_warning(df_flags)

    # ============================================================
    # EXPORT DATABASE
    # ============================================================
    st.divider()
    st.subheader("📤 Export Database")

    st.info("Download a full export of all database tables as CSV files.")

    if st.button("📦 Export All Tables"):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_buffer = io.BytesIO()

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for table in tables:
                    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)

                    zip_file.writestr(
                        f"{table}_{timestamp}.csv",
                        csv_buffer.getvalue()
                    )

        zip_buffer.seek(0)

        st.download_button(
            label="⬇️ Download Export",
            data=zip_buffer,
            file_name=f"girft_database_export_{timestamp}.zip",
            mime="application/zip"
        )




