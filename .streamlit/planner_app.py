import streamlit as st
import pandas as pd
import os
import girft_planner_app as app

staff_list = app.load_data('staff_list.csv')

staff_names = staff_list['staff_member'].to_list()
staff_names.sort()

activity_list = app.load_data('programme_categories.csv')

activity_names = activity_list['programme_categories'].to_list()
activity_names.sort()

leave_calendar_df = app.load_or_update_leave_file('annual_leave_calendar.csv'
                                                  ,staff_names,'days_leave')

onsite_calendar_df = app.load_or_update_leave_file('on_site_calendar.csv'
                                                  ,staff_names,'on_site_days')

activity_calendar_df = app.load_or_update_planner_file('activity_calendar.csv'
                                                  ,staff_names,activity_names)
#print(leave_calendar_df)

leave_file_path = "annual_leave_calendar.csv"

onsite_file_path = "on_site_calendar.csv"

activity_file_path = "activity_calendar.csv"

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
    # Summary
    # ------------------------------------------------
    # st.subheader("Summary Stats")

    # summary = leave_calendar_df.groupby("staff_member")["days_leave"].sum().reset_index()
    # summary.columns = ["Staff", "Total Leave (days)"]

    # st.dataframe(summary, hide_index=True)

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
    # Summary
    # ------------------------------------------------
    # st.subheader("On-Site Summary Stats")

    # summary = onsite_calendar_df.groupby("staff_member")["on_site_days"].sum().reset_index()
    # summary.columns = ["Staff", "Total On-Site (days)"]

    # st.dataframe(summary, hide_index=True)

with tab3:
    
    st.title("📅 Programme of Work")
    st.subheader("✏️ Enter Programme of Work")

    st.subheader("✏️ Edit Programme Activity for a Specific Team Member")

    selected_staff_act = st.selectbox("Select Programme staff member", staff_list)

    # Filter correctly
    staff_act_df = (
        activity_calendar_df[activity_calendar_df["staff_member"] == selected_staff_act]
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
        activity_calendar_df.loc[
            activity_calendar_df["staff_member"] == selected_staff_act,
            activity_cols
        ] = edited_act_df[activity_cols].values

        save_data(activity_calendar_df, "programme-activity")

        st.success("All Programme Activity Changes Saved")

with tab4:

    st.title("📅 Activity Overview")

    st.set_page_config(layout="wide")
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

    st.subheader("📊 Weekly Programme Activity Breakdown")
    fig = app.make_activity_chart(activity_calendar_df, activity_names)
    st.plotly_chart(fig, use_container_width=True)

