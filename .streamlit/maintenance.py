import streamlit as st
import pandas as pd
from planner_functions import update_staff_list, update_programme_list
import data_store as ds
import sqlite3
import planner_functions as pf
import io
from datetime import datetime, date, timedelta
import zipfile
from werkzeug.security import generate_password_hash

#DB_PATH = "girft_capacity_planner.db"


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

        # -----------------------------------------------------------------
        # ARCHIVE SECTION
        # -----------------------------------------------------------------
        st.subheader("🗑️ Archive Staff Member")

        # ---------------------------
        # Load active staff from DB
        # ---------------------------
        archive_staff = (
            staff_list.loc[
                staff_list["archive_flag"] == 0,
                "staff_member"
            ]
            .dropna()
            .sort_values()
            .tolist()
        )

        if archive_staff:

            staff_to_archive = st.selectbox(
                "Select staff member to archive",
                archive_staff,
                index=None
            )

            if st.button("Archive Selected Staff"):

                pf.archive_staff(
                    staff_to_archive
                )

                ds.load_or_refresh_all()

                st.success(
                    f"{staff_to_archive} archived successfully."
                )

                st.rerun()

            else:

                st.info("No active staff to archive.")

                # Optional: refresh cached data
                ds.load_or_refresh_all()

                st.rerun()   # ← force immediate refresh
            
        # -----------------------------------------------------------------
        # RESTORE ARCHIVED STAFF
        # -----------------------------------------------------------------
        st.subheader("♻️ Restore Archived Staff Member")

        # ---------------------------
        # Load archived staff from DB
        # ---------------------------
        archived_staff = (
                    staff_list.loc[
                        staff_list["archive_flag"] == 1,
                        "staff_member"
                    ]
                    .dropna()
                    .sort_values()
                    .tolist()
                )

        if archived_staff:
            staff_to_restore = st.selectbox(
                "Select archived staff member to restore",
                archived_staff, index=None
            )

            # ---------------------------
            # RESTORE STAFF MEMBER
            # ---------------------------
            if st.button("Restore Selected Staff"):

                pf.restore_staff(
                    staff_to_restore
                )

                ds.load_or_refresh_all()

                st.success(
                    f"{staff_to_restore} restored successfully."
                )

                st.rerun()

            else:
                st.info("No archived staff to restore.")

        st.divider()
        #st.subheader("🔐 Password Reset")

        # Pull all staff (active + archived) so you can reset anyone
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT staff_member
                FROM staff_list
                ORDER BY staff_member
            """)
            all_staff = [r[0] for r in cur.fetchall()]

        # ---------------------------
        # Reset an individual password
        # ---------------------------
        st.subheader("🔐 Reset an Individual Password")

        staff_members = sorted(
                                staff_list["staff_member"]
                                .dropna()
                                .tolist()
                                )

        staff_to_reset = st.selectbox(
            "Select staff member",
            staff_members,
            index=None,
            key="reset_pw_staff_member"
        )

        temp_pw = st.text_input(
            "Temporary password",
            value="Temporary123!",
            type="password",
            key="reset_pw_temp"
        )

        if st.button(
            "Reset selected user's password",
            key="reset_pw_btn"
        ):

            if not staff_to_reset:

                st.error(
                    "Please select a staff member."
                )

            else:

                selected_row = staff_list[
                    staff_list["staff_member"]
                    == staff_to_reset
                ]

                if selected_row.empty:

                    st.error(
                        f"No user found for {staff_to_reset}"
                    )

                else:

                    username = (
                        selected_row.iloc[0]["username"]
                    )

                    pf.reset_individual_password(
                        username=username,
                        temp_password=temp_pw
                    )

                    st.success(
                        f"Password reset for "
                        f"{staff_to_reset}"
                    )

                    ds.load_or_refresh_all()

                    st.rerun()

        # ---------------------------
        # Reset ALL passwords (dangerous)
        # ---------------------------
        st.subheader("⚠️ Reset ALL Passwords")

        st.warning("This will reset EVERY user's password and force a change on next login.")

        temp_pw_all = st.text_input(
            "Temporary password for ALL users",
            value="Temporary123!",
            type="password",
            key="reset_all_temp"
        )

        confirm = st.text_input(
            "Type RESET ALL to confirm",
            key="reset_all_confirm"
        )

        if st.button("⚠️ Reset ALL Passwords", key="reset_all_btn"):
            if confirm.strip().upper() != "RESET ALL":
                st.error("Confirmation not valid. Type RESET ALL to proceed.")
            else:
                #hashed_all = generate_password_hash(temp_pw_all)

                pf.reset_all_passwords(
                                        temp_password=temp_pw_all
                                        )

            st.success("All passwords reset. Everyone will be forced to change their password on next login.")
            ds.load_or_refresh_all()
            st.rerun()

        # -----------------------------------------------------------------
        # Change User Access level
        # -----------------------------------------------------------------
        st.subheader("🔐 Change Staff Member Access Level")

        # Load staff
        available_staff = (
                            staff_list.loc[
                                staff_list["archive_flag"] == 0,
                                "staff_member"
                            ]
                            .dropna()
                            .sort_values()
                            .tolist()
                            )   

        if available_staff:

            staff_to_change = st.selectbox(
                "Select staff member to update access for",
                available_staff,
                index=None
            )

            st.markdown("""
            #### Access levels are:

            - **Admin** – Access to all parts of the app including maintenance  
            - **User** – Access to input and view own data  
            - **Viewer** – Access to view the dashboard
            """)

            user_access_level = st.selectbox(
                "User Access Level",
                options=["admin", "user", "viewer"],
                key="user_access_level"
            )

            if st.button("Change Access Level for Selected Staff"):

                if not staff_to_change:

                    st.error(
                        "Please select a staff member."
                    )

                else:

                    pf.update_access_level(
                        staff_to_change,
                        user_access_level
                    )

                    ds.load_or_refresh_all()

                    st.success(
                        f"{staff_to_change} access level changed successfully."
                    )

                    st.rerun()



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

        # ----------------------------
        # Dynamic Programme Groups
        # ----------------------------
        programme_group_options = sorted(
            programme_list.loc[
                programme_list["archive_flag"] == 0, "programme_group"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        programme_group_options_with_new = programme_group_options + ["➕ Add new group"]

        selected_group = st.selectbox(
            "Programme Group",
            programme_group_options_with_new
        )

        # Allow new group entry
        if selected_group == "➕ Add new group":
            programme_group = st.text_input("Enter new Programme Group")
        else:
            programme_group = selected_group

        # ----------------------------
        # ADD PROGRAMME BUTTON
        # ----------------------------
        if st.button("➕ Add Programme"):

            # ----------------------------
            # Clean inputs
            # ----------------------------
            new_programme = new_programme.strip()
            programme_group = programme_group.strip().title() if programme_group else ""

            # ----------------------------
            # Validate inputs
            # ----------------------------
            if not new_programme:
                st.error("Please enter a programme category.")
                return

            if not programme_group:
                st.error("Please select or enter a programme group.")
                return

            # ----------------------------
            # 🚫 Prevent duplicate programmes
            # ----------------------------
            existing_programmes = programme_list["programme_categories"].str.strip().str.lower()

            if new_programme.lower() in existing_programmes.values:
                st.error("This programme category already exists.")
                return

            # ----------------------------
            # ⚠️ Handle duplicate groups safely
            # ----------------------------
            existing_groups = programme_list["programme_group"].str.strip().str.lower()

            if programme_group.lower() in existing_groups.values:
                if selected_group == "➕ Add new group":
                    st.warning("This programme group already exists — using existing group.")

            # ----------------------------
            # Save to database
            # ----------------------------
            update_programme_list(
                new_programme=new_programme,
                programme_type=programme_type,
                programme_group=programme_group
            )

            # Refresh data
            ds.load_or_refresh_all()

            st.success(f"{new_programme} added successfully.")
            st.rerun()

        # ----------------------------
        # Archive existing programmes
        # ----------------------------
        st.subheader("🗑️ Archive Programme Category")

        active_programmes = (
                            programme_list.loc[
                                programme_list["archive_flag"] == 0,
                                "programme_categories"
                            ]
                            .dropna()
                            .sort_values()
                            .tolist()
                            )

        programme_to_archive = st.selectbox(
            "Select programme to archive",
            active_programmes,
            index=None
            )

        if st.button("Archive Selected Programme"):

            if not programme_to_archive:

                st.error(
                    "Please select a programme."
                )

            else:

                pf.archive_programme(
                    programme_to_archive
                )

                ds.load_or_refresh_all()

                st.success(
                    f"{programme_to_archive} archived successfully."
                )

                st.rerun()

        # ----------------------------
        # Restore archived programmes
        # ----------------------------
        st.subheader("♻️ Restore Programme Category")

        archived_programmes = (
                                programme_list.loc[
                                    programme_list["archive_flag"] == 1,
                                    "programme_categories"
                                ]
                                .dropna()
                                .sort_values()
                                .tolist()
                                )

        programme_to_restore = st.selectbox(
            "Select programme to restore",
            archived_programmes,
            index=None
        )

        if st.button("Restore Selected Programme"):

            if not programme_to_restore:

                st.error(
                    "Please select a programme."
                )

            else:

                pf.restore_programme(
                    programme_to_restore
                    )

                ds.load_or_refresh_all()

                st.success(
                    f"{programme_to_restore} restored successfully."
                )

                st.rerun()

        # ============================================================
        # 🔄 FIX PROGRAMME GROUP (PRIMARY ACTION)
        # ============================================================
        st.subheader("🔄 Fix Programme Group")

        programme_data = (
                        programme_list.loc[
                            programme_list["archive_flag"] == 0,
                            ["programme_categories", "programme_group"]
                        ]
                        .sort_values("programme_categories")
                        )
        
        programme_names = (
                            programme_data["programme_categories"]
                            .dropna()
                            .tolist()
                            )
                        
        programme_to_update = st.selectbox(
            "Select programme to update",
            programme_names,
            index=None,
            key="fix_programme_select"
        )

        # Get current group (for display)
        current_group = None

        if programme_to_update:

            selected_row = programme_data[
                programme_data["programme_categories"]
                == programme_to_update
            ]

            if not selected_row.empty:

                current_group = (
                    selected_row.iloc[0]["programme_group"]
                )

                st.info(
                    f"Current group: **{current_group}**"
                )

        # Existing groups
        existing_groups = sorted(
                                programme_data["programme_group"]
                                .dropna()
                                .unique()
                                .tolist()
                                )
        group_options = existing_groups + ["➕ Add new group"]

        selected_group = st.selectbox(
            "Select new programme group",
            group_options,
            index=None,
            key="fix_programme_group_select"
        )

        if selected_group == "➕ Add new group":
            new_group_input = st.text_input("Enter new programme group", key="fix_new_group")
            new_group = new_group_input.strip().title() if new_group_input else None
        else:
            new_group = selected_group

        if st.button("Update Programme Group", key="update_programme_group_btn"):

            if not programme_to_update:
                st.error("Please select a programme.")
            
            elif not new_group:
                st.error("Please select or enter a programme group.")
            
            elif new_group == current_group:
                st.warning("Programme is already in this group.")
            
            else:
                pf.update_programme_group(
                                        programme_to_update,
                                        new_group
                                        )

                ds.load_or_refresh_all()

                st.success(
                            f"{programme_to_update} moved to '{new_group}'."
                            )

                st.rerun()


        # ============================================================
        # ❌ DELETE PROGRAMME CATEGORY (SAFE)
        # ============================================================
        st.subheader("❌ Delete Programme Category")

        st.warning(
            "This permanently deletes a programme category. "
            "It is only allowed if NO activity has been recorded against it."
        )

        all_programmes = (
                        programme_list["programme_categories"]
                        .dropna()
                        .sort_values()
                        .tolist()
                        )

        programme_to_delete = st.selectbox(
            "Select programme to delete",
            all_programmes,
            index=None,
            key="delete_programme_select"
        )

        confirm_delete = st.text_input(
            "Type DELETE to confirm",
            key="delete_programme_confirm"
        )

        if st.button("❌ Delete Programme", key="delete_programme_btn"):

            if confirm_delete.strip().upper() != "DELETE":
                st.error("Please type DELETE to confirm.")
            
            elif not programme_to_delete:
                st.error("Please select a programme.")
            
            else:
                usage_count = len(
                                programme_calendar_df[
                                    programme_calendar_df["programme_category"]
                                    == programme_to_delete
                                ]
                                )

                if usage_count > 0:
                    st.error(
                        f"Cannot delete '{programme_to_delete}' — "
                        f"it is used in programme activity ({usage_count} records)."
                    )
                else:
                    if st.button(
                        "❌ Delete Programme",
                        key="delete_programme_btn"
                        ):

                        if confirm_delete.strip().upper() != "DELETE":

                            st.error(
                                "Please type DELETE to confirm."
                            )

                        elif not programme_to_delete:

                            st.error(
                                "Please select a programme."
                            )

                        else:

                            usage_count = len(
                                programme_calendar_df[
                                    programme_calendar_df[
                                        "programme_category"
                                    ] == programme_to_delete
                                ]
                            )

                            if usage_count > 0:

                                st.error(
                                    f"Cannot delete '{programme_to_delete}' "
                                    f"because it is used in "
                                    f"{usage_count} activity records."
                                )

                            else:

                                pf.delete_programme(
                                    programme_to_delete
                                )

                                ds.load_or_refresh_all()

                                st.success(
                                    f"{programme_to_delete} deleted successfully."
                                )

                                st.rerun()

    with st.expander("🚨 Data Entry Checklist"):
        
        st.subheader("Status for Previous Week") 

        today = date.today()
        week_commencing = today - timedelta(days=today.weekday() + 7)

        df_flags = pf.get_weekly_data_entry_status(
        staff_list,
        programme_calendar_df,
        leave_calendar_df,
        week_commencing
        )

        pf.render_data_entry_checklist(df_flags)

    # ============================================================
    # EXPORT DATABASE
    # ============================================================
    st.divider()
    # ============================================================
    # EXPORT DATASETS
    # ============================================================

    st.divider()
    st.subheader("📤 Export Data")

    st.info(
        "Download a full export of all datasets as CSV files."
    )

    if st.button("📦 Export All Data"):

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        zip_buffer = io.BytesIO()

        datasets = {
            "staff_list": st.session_state.staff_list,
            "programme_categories": st.session_state.programme_list,
            "programme_activity": st.session_state.programme_calendar_df,
            "leave_calendar": st.session_state.leave_calendar_df,
            "on_site_calendar": st.session_state.onsite_calendar_df,
        }

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for dataset_name, df in datasets.items():

                csv_buffer = io.StringIO()

                df.to_csv(
                    csv_buffer,
                    index=False
                )

                zip_file.writestr(
                    f"{dataset_name}_{timestamp}.csv",
                    csv_buffer.getvalue()
                )

        zip_buffer.seek(0)

        st.download_button(
            label="⬇️ Download Export",
            data=zip_buffer,
            file_name=(
                f"girft_data_export_"
                f"{timestamp}.zip"
            ),
            mime="application/zip"
        )




