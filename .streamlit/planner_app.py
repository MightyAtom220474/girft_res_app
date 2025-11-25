import streamlit as st
import pandas as pd
import os
import girft_planner_app as app

staff_list = app.load_staff_data('data/staff_list.csv')

#st.write(staff_list)

staff_names = staff_list['staff_member'].to_list()
staff_names.sort()

leave_calendar_df = app.load_or_update_leave_file('annual_leave_calendar.csv'
                                                  ,staff_names,'days_leave')

onsite_calendar_df = app.load_or_update_leave_file('on_site_calendar.csv'
                                                  ,staff_names,'on_site_days')
#print(leave_calendar_df)

leave_file_path = "annual_leave_calendar.csv"

onsite_file_path = "on_site_calendar.csv"

def save_data(df,file_type):
    if file_type == "leave":
        df.to_csv(leave_file_path, index=False)
    else:
        df.to_csv(onsite_file_path, index=False)
# set up separate tabs for leave and programme
tab1, tab2, tab3 = st.tabs(["Annual Leave","On-Site","Programme of Work"])

with tab1:

    st.title("📅 Weekly Leave Planner")
    # ------------------------------------------------
    # Select staff to edit
    # ------------------------------------------------
    st.subheader("✏️ Edit Leave for a Specific Team Member")

    selected_staff = st.selectbox("Select staff member", staff_list)

    staff_df = leave_calendar_df[leave_calendar_df["staff_member"] == selected_staff].copy().reset_index(drop=True)

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
        leave_calendar_df.loc[leave_calendar_df["staff_member"] == selected_staff, "days_leave"] = edited_df["days_leave"]
        save_data(leave_calendar_df,"leave")
        st.success("All Changes Saved")

    # ------------------------------------------------
    # Weekly calendar
    # ------------------------------------------------
    st.subheader("📊 Team Leave Calendar View (Weekly Heatmap)")

    pivot = leave_calendar_df.pivot_table(
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

    # # Manual gradient colouring without matplotlib
    # def cell_color(val):
    #     # Scale 0–5 days (feel free to adjust)
    #     max_days = 5
    #     intensity = min(val / max_days, 1)
    #     r = int(255 * intensity)
    #     g = int(200 * (1 - intensity))
    #     b = 0
    #     return f"background-color: rgb({r}, {g}, {b})"

    styled = pivot.style.applymap(cell_color)
    st.dataframe(styled, use_container_width=True)

    # ------------------------------------------------
    # Summary
    # ------------------------------------------------
    st.subheader("Summary Stats")

    summary = leave_calendar_df.groupby("staff_member")["days_leave"].sum().reset_index()
    summary.columns = ["Staff", "Total Leave (days)"]

    st.dataframe(summary, hide_index=True)

with tab2:

    st.title("📅 Weekly On-Site Planner")
    # ------------------------------------------------
    # Select staff to edit
    # ------------------------------------------------
    st.subheader("✏️ Edit On-Site Days for a Specific Team Member")

    selected_staff_os = st.selectbox("Select On-site staff member", staff_list)

    staff_os_df = onsite_calendar_df[onsite_calendar_df["staff_member"] == selected_staff].copy().reset_index(drop=True)

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
        onsite_calendar_df.loc[onsite_calendar_df["staff_member"] == selected_staff, "on_site_days"] = edited_os_df["on_site_days"]
        save_data(onsite_calendar_df,"on-site")
        st.success("All Changes Saved")

    # ------------------------------------------------
    # Weekly calendar
    # ------------------------------------------------
    st.subheader("📊 Team On-Site View (Weekly Heatmap)")

    pivot = onsite_calendar_df.pivot_table(
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

    # # Manual gradient colouring without matplotlib
    # def cell_color(val):
    #     # Scale 0–5 days (feel free to adjust)
    #     max_days = 5
    #     intensity = min(val / max_days, 1)
    #     r = int(255 * intensity)
    #     g = int(200 * (1 - intensity))
    #     b = 0
    #     return f"background-color: rgb({r}, {g}, {b})"

    styled = pivot.style.applymap(cell_color)
    st.dataframe(styled, use_container_width=True)

    # ------------------------------------------------
    # Summary
    # ------------------------------------------------
    st.subheader("On-Site Summary Stats")

    summary = onsite_calendar_df.groupby("staff_member")["on_site_days"].sum().reset_index()
    summary.columns = ["Staff", "Total On-Site (days)"]

    st.dataframe(summary, hide_index=True)

with tab3:
    
    st.title("📅 Programme of Work")
    st.subheader("✏️ Enter Progamme of Work")