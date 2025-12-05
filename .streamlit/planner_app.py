import streamlit as st
import pandas as pd
import os
from planner_functions import load_data, load_or_update_leave_file\
    ,load_or_update_planner_file,make_activity_chart
import data_store as ds


def app():
    # initial load of staff_list in order to build calendars if they don't exist
    if ds.staff_list is None:
        ds.staff_list = load_data("staff_list.csv")

    # print(staff_list)

    staff_names = ds.staff_list['staff_member'].to_list()
    staff_names.sort()
    
    if ds.activity_list is None:
        ds.activity_list = load_data('programme_categories.csv')

    activity_names = ds.activity_namesactivity_list['programme_categories'].to_list()
    activity_names.sort()

    if ds.leave_calendar_df is None:
        ds.leave_calendar_df = load_or_update_leave_file('annual_leave_calendar.csv'
                                                    ,staff_names,'days_leave')
    if ds.onsite_calendar_df_calendar_df is None:
        ds.onsite_calendar_df = load_or_update_leave_file('on_site_calendar.csv'
                                                    ,staff_names,'on_site_days')
    if ds.programme_calendar_df is None:
        ds.programme_calendar_df = load_or_update_planner_file('programme_calendar.csv'
                                                    ,staff_names,activity_names)
    #print(leave_calendar_df)

    leave_file_path = "annual_leave_calendar.csv"

    onsite_file_path = "on_site_calendar.csv"

    activity_file_path = "programme_calendar.csv"

    def save_data(df,file_type):
        if file_type == "leave":
            df.to_csv(leave_file_path, index=False)
        elif file_type == "activity":
            df.to_csv(activity_file_path, index=False)
        else:
            df.to_csv(onsite_file_path, index=False)

    # set up separate tabs for leave, on-site, and programme
    tab1, tab2, tab3, tab4 = st.tabs(["Annual Leave","On-Site","Programme of Work","All Activity"])

    with tab1:

        st.title("📅 Weekly Leave Planner")
        # ------------------------------------------------
        # Select staff to edit
        # ------------------------------------------------
        st.subheader("✏️ Edit Leave for a Specific Team Member")

        # update staff names in case any have been changed in maintenance page
        staff_names  = ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"].tolist()
        staff_names.sort()

        selected_staff = st.selectbox("Select staff member", staff_names)

        staff_df = ds.leave_calendar_df[ds.leave_calendar_df["staff_member"] == selected_staff].copy().reset_index(drop=True)

        # ------------------------------------------------
        # Editable table for selected staff
        # ------------------------------------------------
        st.write(f"### Editing: {selected_staff}")

        edited_df = st.data_editor(
            staff_df,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "week_number": st.column_config.NumberColumn("Week", disabled=True),
                "week_commencing": st.column_config.DateColumn(
                    "Week Commencing (Mon)", disabled=True
                ),
                "days_leave": st.column_config.NumberColumn(
                    "Days of Leave",
                    help="Enter days or fractions (e.g. 0.5)",
                    step=0.5
                ),
                "staff": st.column_config.TextColumn("Staff", disabled=True)
            }
        )

        # ------------------------------------------------
        # Save updated data
        # ------------------------------------------------
        if st.button("💾 Save Changes"):
            ds.leave_calendar_df.loc[ds.leave_calendar_df["staff_member"] == selected_staff, "days_leave"] = edited_df["days_leave"]
            save_data(ds.leave_calendar_df,"leave")
            st.success("All Changes Saved")

    with tab2:

        st.title("📅 Weekly On-Site Planner")

        # update staff names in case any have been changed in maintenance page
        staff_names  = ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"].tolist()
        staff_names.sort()
        # ------------------------------------------------
        # Select staff to edit
        # ------------------------------------------------
        st.subheader("✏️ Edit On-Site Days for a Specific Team Member")

        selected_staff_os = st.selectbox("Select On-site staff member", ds.staff_list)

        staff_os_df = ds.onsite_calendar_df[ds.onsite_calendar_df["staff_member"] == selected_staff].copy().reset_index(drop=True)

        # ------------------------------------------------
        # Editable table for selected staff
        # ------------------------------------------------
        st.write(f"### Editing: {selected_staff_os}")

        edited_os_df = st.data_editor(
            staff_os_df,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "week_number": st.column_config.NumberColumn("Week", disabled=True),
                "week_commencing": st.column_config.DateColumn(
                    "Week Commencing (Mon)", disabled=True
                ),
                "on_site_days": st.column_config.NumberColumn(
                    "Days on Site",
                    help="Enter days or fractions (e.g. 0.5)",
                    step=0.5
                ),
                "staff": st.column_config.TextColumn("Staff", disabled=True)
            }
        )

        # ------------------------------------------------
        # Save updated data
        # ------------------------------------------------
        if st.button("💾 Save On-Site Changes"):
            ds.onsite_calendar_df.loc[ds.onsite_calendar_df["staff_member"] == selected_staff, "on_site_days"] = edited_os_df["on_site_days"]
            save_data(ds.onsite_calendar_df,"on-site")
            st.success("All Changes Saved")

    with tab3:
        
        st.title("📅 Programme of Work")
        st.subheader("✏️ Enter Programme of Work")

        st.subheader("✏️ Edit Programme Activity for a Specific Team Member")

        # update staff names in case any have been changed in maintenance page
        staff_names  = ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"].tolist()
        staff_names.sort()

        selected_staff_act = st.selectbox("Select Programme staff member", ds.staff_list)

        # Filter correctly
        staff_act_df = (
            ds.programme_calendar_df[ds.programme_calendar_df["staff_member"] == selected_staff_act]
            .copy()
            .reset_index(drop=True)
        )

        # Identify activity columns
        protected_cols = ["staff_member", "week_number", "week_commencing"]
        activity_cols = [c for c in staff_act_df.columns if c not in protected_cols]

        # Build dynamic column config
        col_config = {
            "staff_member": st.column_config.TextColumn("Staff", disabled=True),
            "week_number": st.column_config.NumberColumn("Week", disabled=True),
            "week_commencing": st.column_config.DateColumn("Week Commencing (Mon)", disabled=True),
        }

        # Add editable configs for each activity column
        for col in activity_cols:
            col_config[col] = st.column_config.NumberColumn(
                col.replace("_", " ").title(),
                step=0.5
            )

        st.write(f"### Editing: {selected_staff_act}")

        edited_act_df = st.data_editor(
            staff_act_df,
            hide_index=True,
            num_rows="fixed",
            column_config=col_config
        )

        # --------------------------
        # Save data back to the main DF
        # --------------------------
        if st.button("💾 Save Programme Activity Changes"):
            ds.programme_calendar_df.loc[
                ds.programme_calendar_df["staff_member"] == selected_staff_act,
                activity_cols
            ] = edited_act_df[activity_cols].values

            save_data(ds.programme_calendar_df, "programme-activity")

            st.success("All Programme Activity Changes Saved")

    with tab4:

        st.title("📅 Activity Overview")

        st.set_page_config(layout="wide")
        # ------------------------------------------------
        # Weekly Leave Calendar
        # ------------------------------------------------
        st.subheader("📊 Team Leave Calendar View (Weekly Heatmap)")

        pivot = ds.leave_calendar_df.pivot_table(
            index="staff_member",
            columns="week_number",
            values="days_leave",
            fill_value=0
        )

        # Manual gradient colouring without matplotlib
        def cell_color(val):
            # Scale 0–5 days (feel free to adjust)
            max_days = 5
            intensity = min(val / max_days, 1)
            r = int(255 * intensity)
            g = int(200 * (1 - intensity))
            b = 0
            return f"background-color: rgb({r}, {g}, {b})"

        staff_col_px = 140
        week_col_px = 22   # works for 52 weeks

        styled = (
            pivot.style
            .applymap(cell_color)
            .format("{:.2f}")
        )

        styles = [
            # Staff row header column
            {
                "selector": "th.row_heading",
                "props": [
                    ("min-width", f"{staff_col_px}px"),
                    ("max-width", f"{staff_col_px}px"),
                    ("white-space", "nowrap")
                    ]
                },
                # Week header columns
                {
                    "selector": "th.col_heading",
                    "props": [
                        ("min-width", f"{week_col_px}px"),
                        ("max-width", f"{week_col_px}px"),
                        ("padding", "2px 4px")
                    ]
                },
                # Week value cells
                {
                    "selector": "td",
                    "props": [
                        ("min-width", f"{week_col_px}px"),
                        ("max-width", f"{week_col_px}px"),
                        ("padding", "2px 4px")
                    ]
                }
            ]

        styled = styled.set_table_styles(styles)

        with st.container():
            st.dataframe(styled, use_container_width=True, height=len(staff_names)*39)

        st.set_page_config(layout="wide")
        # ------------------------------------------------
        # Weekly On-Site Calendar
        # ------------------------------------------------
        st.subheader("📊 Team On-Site View (Weekly Heatmap)")

        pivot = ds.onsite_calendar_df.pivot_table(
            index="staff_member",
            columns="week_number",
            values="on_site_days",
            fill_value=0
        )

        # Manual gradient colouring without matplotlib
        def cell_color(val):
            # Scale 0–5 days (feel free to adjust)
            max_days = 5
            intensity = min(val / max_days, 1)
            r = 0
            g = int(200 * (1 - intensity))
            b = int(255 * intensity)
            return f"background-color: rgb({r}, {g}, {b})"

        staff_col_px = 140
        week_col_px = 22   # works for 52 weeks

        styled = (
            pivot.style
            .applymap(cell_color)
            .format("{:.2f}")
        )

        styles = [
            # Staff row header column
            {
                "selector": "th.row_heading",
                "props": [
                    ("min-width", f"{staff_col_px}px"),
                    ("max-width", f"{staff_col_px}px"),
                    ("white-space", "nowrap")
                    ]
                },
                # Week header columns
                {
                    "selector": "th.col_heading",
                    "props": [
                        ("min-width", f"{week_col_px}px"),
                        ("max-width", f"{week_col_px}px"),
                        ("padding", "2px 4px")
                    ]
                },
                # Week value cells
                {
                    "selector": "td",
                    "props": [
                        ("min-width", f"{week_col_px}px"),
                        ("max-width", f"{week_col_px}px"),
                        ("padding", "2px 4px")
                    ]
                }
            ]

        styled = styled.set_table_styles(styles)

        with st.container():
            st.dataframe(styled, use_container_width=True, height=len(staff_names)*39)

        # summary of weekly programme activity
        st.subheader("📊 Weekly Programme Activity Breakdown")
        fig = make_activity_chart(ds.programme_calendar_df, activity_names)
        
        fig.update_layout(
                        width=1200,
                        height=1200
                        )
        
        st.plotly_chart(fig, use_container_width=True)

    # convert leave days to hours ready to compare with contracted hours
    ds.leave_calendar_df['leave_hours'] = ds.leave_calendar_df['days_leave']*7.5

    # merge leave calendar with staff list
    ds.staff_leave_merged_df = ds.leave_calendar_df.merge(
        ds.staff_list,
        on="staff_member",
        how="left"     # or "inner" if you only want matching rows
    )

    # calculate amount of available staff
    ds.staff_leave_merged_df['avail_hours'] = ds.staff_leave_merged_df['hours_pw']-ds.staff_leave_merged_df['leave_hours']

    # merge programme calendar with staff list
    ds.staff_prog_merged_df = ds.programme_calendar_df.merge(
        ds.staff_list,
        on="staff_member",
        how="left"     # or "inner" if you only want matching rows
    )

    # calculate amount of available staff
    ds.staff_prog_merged_df['avail_hours'] = ds.staff_prog_merged_df['hours_pw']-ds.staff_prog_merged_df['leave_hours']

    # calculate amount of available staff
    ds.staff_prog_merged_df['non-deployable hours'] = ds.staff_prog_merged_df['avail_hours']*(1-ds.staff_prog_merged_df['deploy_ratio'])


