import streamlit as st
import pandas as pd
import os
import planner_functions as pf
import data_store as ds


def planner():
    
    ds.load_or_refresh_all()

    leave_file_path = "annual_leave_calendar.csv"

    onsite_file_path = "on_site_calendar.csv"

    programme_file_path = "programme_calendar.csv"

    # set up separate tabs for leave, on-site, and programme
    tab1, tab2, tab3, tab4 = st.tabs(["Programme of Work","Annual Leave","On-Site","All Activity"])

    with tab1:
        
        st.title("📅 Programme of Work")
        st.subheader("✏️ Add or Edit Programme Activity for a Specific Team Member")

        # ---------------------------
        # 1️⃣ Load active staff
        # ---------------------------
        staff_names = ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"].sort_values().tolist()

        selected_staff = st.selectbox("Select Programme Team Member", staff_names)

        # ---------------------------
        # 2️⃣ Week commencing
        # ---------------------------
        week_commencing = st.date_input(
            "Select Week Commencing (Monday)",
            help="Choose the Monday of the week you want to enter activity for"
        )

        if week_commencing.weekday() != 0:
            st.warning("⚠️ The week commencing date must be a Monday.")

        # ---------------------------
        # 3️⃣ Programme group filter
        # ---------------------------
        # Only non-archived programmes
        active_programmes = ds.programme_list.loc[ds.programme_list["archive_flag"] == 0].copy()

        programme_groups = ["All"] + sorted(active_programmes["programme_group"].dropna().unique().tolist())
        selected_group = st.selectbox("Select Programme Group", programme_groups, index=0)

        if selected_group == "All":
            programmes_filtered = active_programmes
        else:
            programmes_filtered = active_programmes.loc[active_programmes["programme_group"] == selected_group]

        # Programme categories to display
        programme_categories_filtered = programmes_filtered["programme_categories"].tolist()

        # ---------------------------
        # 4️⃣ Determine activity columns in planner
        # ---------------------------
        base_cols = {"staff_member", "week_number", "week_commencing", "Total Act Hours"}
        activity_cols = [c for c in ds.programme_calendar_df.columns if c not in base_cols]

        # Only include activity columns that are in the filtered programme categories
        activity_cols = [c for c in activity_cols if c in programme_categories_filtered]

        # ---------------------------
        # 5️⃣ Load existing row if exists
        # ---------------------------
        mask = (
            (ds.programme_calendar_df["staff_member"] == selected_staff) &
            (ds.programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing))
        )

        if mask.any():
            staff_row = ds.programme_calendar_df.loc[mask].iloc[0]
        else:
            staff_row = pd.Series({col: 0.0 for col in activity_cols})

        # ---------------------------
        # 6️⃣ Build selectboxes for each activity
        # ---------------------------
        st.write(f"### Editing Programme Activity for: **{selected_staff}**")
        st.write(f"#### Week Commencing: **{week_commencing}**")

        # 0 → 37.5 in 0.5 steps
        hour_values = [x * 0.5 for x in range(0, 76)]

        activity_inputs = {}

        for col in activity_cols:
            default_value = float(staff_row[col]) if col in staff_row else 0.0
            pretty_name = col.replace("_", " ").title()

            activity_inputs[col] = st.selectbox(
                pretty_name,
                hour_values,
                index=hour_values.index(default_value) if default_value in hour_values else 0
            )

        # ---------------------------
        # 7️⃣ Save button
        # ---------------------------
        if st.button("💾 Save Programme Activity Changes"):
            updated_row = {
                "staff_member": selected_staff,
                "week_commencing": pd.to_datetime(week_commencing),
                "week_number": pd.to_datetime(week_commencing).isocalendar().week,
                **activity_inputs
            }

            if mask.any():
                # Update existing row
                ds.programme_calendar_df.loc[mask, activity_cols] = pd.DataFrame([updated_row])[activity_cols].values
                action = "updated"
            else:
                # Add new row
                ds.programme_calendar_df = pd.concat(
                    [ds.programme_calendar_df, pd.DataFrame([updated_row])],
                    ignore_index=True
                )
                action = "added"

            # Save to CSV
            pf.save_data(ds.programme_calendar_df, "programme_calendar.csv")

            st.success(f"Programme activity successfully {action} for {selected_staff} on week {week_commencing}")
    
    with tab2:

        st.title("📅 Weekly Leave Planner")
        # ------------------------------------------------
        # Select staff to edit
        # ------------------------------------------------
        st.subheader("✏️ Add or Edit Leave for a Team Member")

        # ------------------------------------------------
        # Select Staff Member
        # ------------------------------------------------
        staff_names = (
            ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"]
            .sort_values()
            .tolist()
        )

        selected_staff = st.selectbox("Select Leave Team Member", staff_names)

        # ------------------------------------------------
        # Pick Week Commencing (Monday only)
        # ------------------------------------------------
        week_commencing = st.date_input(
            "Select Week Commencing (Monday)",
            help="Choose the Monday of the week the leave applies to"
        )

        # Optional validation (ensure it's a Monday)
        if week_commencing.weekday() != 0:
            st.warning("⚠️ The week commencing date must be a Monday.")

        # ------------------------------------------------
        # Leave Days Input (0.5 to 5 in 0.5 increments)
        # ------------------------------------------------
        days_leave = st.selectbox(
            "Number of Leave Days",
            [x * 0.5 for x in range(0, 11)],  # 0, 0.5, ..., 5
            help="Select whole or half days (max 5)"
        )

        # ------------------------------------------------
        # Save Button
        # ------------------------------------------------
        if st.button("💾 Save"):
            # Check if row already exists for staff + week
            mask = (
                (ds.leave_calendar_df["staff_member"] == selected_staff) &
                (ds.leave_calendar_df["week_commencing"] == pd.to_datetime(week_commencing))
            )

            if mask.any():
                # Update existing row
                ds.leave_calendar_df.loc[mask, "days_leave"] = days_leave
                action = "updated"
            else:
                # Add new row
                new_row = {
                    "staff_member": selected_staff,
                    "week_commencing": pd.to_datetime(week_commencing),
                    "week_number": pd.to_datetime(week_commencing).isocalendar().week,
                    "days_leave": days_leave
                }
                ds.leave_calendar_df = pd.concat(
                    [ds.leave_calendar_df, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                action = "added"

            # Save file
            pf.save_data(ds.leave_calendar_df, leave_file_path)

            st.success(f"Leave successfully {action} for {selected_staff} on week {week_commencing}")

    with tab3:

        st.title("📅 Weekly On-Site Planner")

        # ------------------------------------------------
        # Load staff names (active only)
        # ------------------------------------------------
        staff_names = (
            ds.staff_list.loc[ds.staff_list["archive_flag"] == 0, "staff_member"]
            .sort_values()
            .tolist()
        )

        # ------------------------------------------------
        # Select Staff Member to Edit
        # ------------------------------------------------
        st.subheader("✏️ Add or Edit On-Site Days for a Specific Team Member")

        selected_staff_os = st.selectbox("Select On-site Team Member", staff_names)

        # ------------------------------------------------
        # Select Week Commencing (Monday)
        # ------------------------------------------------
        week_commencing_os = st.date_input(
            "Select Week Commencing (Monday)",
            help="Choose the Monday of the week the on-site days apply to"
        )

        # Make sure the date is a Monday
        if week_commencing_os.weekday() != 0:
            st.warning("⚠️ The week commencing date must be a Monday.")

        # ------------------------------------------------
        # Days On Site Input (0 - 5 in 0.5 increments)
        # ------------------------------------------------
        on_site_days = st.selectbox(
            "Number of On-Site Days",
            [x * 0.5 for x in range(0, 11)],    # 0 → 5 in half-day steps
            help="Select whole or half days (max 5)"
        )

        # ------------------------------------------------
        # Save Button
        # ------------------------------------------------
        if st.button("💾 Save On-Site Changes"):
            # Identify whether row already exists
            mask = (
                (ds.onsite_calendar_df["staff_member"] == selected_staff_os) &
                (ds.onsite_calendar_df["week_commencing"] == pd.to_datetime(week_commencing_os))
            )

            if mask.any():
                # Update existing row
                ds.onsite_calendar_df.loc[mask, "on_site_days"] = on_site_days
                action = "updated"
            else:
                # Insert new record
                new_row = {
                    "staff_member": selected_staff_os,
                    "week_commencing": pd.to_datetime(week_commencing_os),
                    "week_number": pd.to_datetime(week_commencing_os).isocalendar().week,
                    "on_site_days": on_site_days
                }
                ds.onsite_calendar_df = pd.concat(
                    [ds.onsite_calendar_df, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                action = "added"

            # Save the file
            pf.save_data(ds.onsite_calendar_df, onsite_file_path)

            st.success(f"On-site days {action} for {selected_staff_os} on week {week_commencing_os}")

    with tab4:

        st.title("📅 Programme Overview")

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
        fig = pf.make_activity_chart(ds.programme_calendar_df, ds.programme_names)
        
        fig.update_layout(
                        width=1200,
                        height=1200
                        )
        
        st.plotly_chart(fig, use_container_width=True)

        


