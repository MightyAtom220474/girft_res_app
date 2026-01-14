import streamlit as st
import pandas as pd
import os
import planner_functions as pf
import data_store as ds


def planner():
    
    if "staff_list" not in st.session_state:
        ds.load_or_refresh_all()
        
    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df
    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df
    staff_names = st.session_state.staff_list
    programme_names = st.session_state.programme_list

    # set up separate tabs for leave, on-site, and programme
    tab1, tab2, tab3, tab4 = st.tabs(["Programme of Work","Annual Leave","On-Site","All Activity"])

    with tab1:
        
        st.title("📅 Programme of Work")
        st.subheader("✏️ Add or Edit Programme Activity for a Specific Team Member")

        # ---------------------------
        # 1️⃣ Load active staff
        # ---------------------------
        staff_names = staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"].sort_values().tolist()

        selected_staff = st.selectbox("Select Programme Team Member", staff_names, index=None)

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
        active_programmes = programme_list.loc[programme_list["archive_flag"] == 0].copy()

        programme_groups = ["All"] + sorted(active_programmes["programme_group"].dropna().unique().tolist())
        selected_group = st.selectbox("Select Programme Group", programme_groups, index=0)

        if selected_group == "All":
            programmes_filtered = active_programmes
        else:
            programmes_filtered = active_programmes.loc[active_programmes["programme_group"] == selected_group]

        # Programme categories to display
        programme_categories_filtered = programmes_filtered["programme_categories"].tolist()

        # ---------------------------
        # Determine activity rows for selected staff & week
        # ---------------------------
        mask = (
            (programme_calendar_df["staff_member"] == selected_staff) &
            (programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing)) &
            (programme_calendar_df["programme_category"].isin(programme_categories_filtered))
        )

        # Filter the relevant rows
        staff_activities = programme_calendar_df.loc[mask].copy()

        # If no activity exists yet, create a default row with zeros
        if staff_activities.empty:
            staff_activities = pd.DataFrame({
                "staff_member": [selected_staff]*len(programme_categories_filtered),
                "week_commencing": [pd.to_datetime(week_commencing)]*len(programme_categories_filtered),
                "week_number": [pd.to_datetime(week_commencing).isocalendar()[1]]*len(programme_categories_filtered),
                "programme_category": programme_categories_filtered,
                "activity_value": [0.0]*len(programme_categories_filtered)
            })

        # ---------------------------
        # 6️⃣ Build selectboxes for each activity
        # ---------------------------
        st.write(f"### Editing Programme Activity for: **{selected_staff}**")
        st.write(f"#### Week Commencing: **{week_commencing}**")

        mask = (
            (programme_calendar_df["staff_member"] == selected_staff) &
            (programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing))
        )

        if mask.any():
            staff_row = programme_calendar_df.loc[mask].iloc[0]
        else:
            staff_row = pd.Series({col: 0.0 for col in programme_categories_filtered})

        # 0 → 37.5 in 0.5 steps
        hour_values = [x * 0.5 for x in range(0, 76)]

        activity_inputs = {}

        for col in programme_categories_filtered:
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
            pf.save_programme_activity(
                selected_staff=selected_staff,
                week_commencing=week_commencing,
                activity_inputs=activity_inputs
            )

            st.success(
                f"Programme activity saved for {selected_staff} "
                f"week commencing {pd.to_datetime(week_commencing).date()}"
            )

            st.rerun()   # ← force immediate refresh
    
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
            st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
            .sort_values()
            .tolist()
        )

        selected_staff = st.selectbox("Select Leave Team Member", staff_names, index=None)

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
        if st.button("💾 Save Leave Changes"):
            pf.save_annual_leave(
                staff_member=selected_staff,
                week_commencing=week_commencing,
                days_leave=days_leave
            )

            st.success(
                f"Leave saved for {selected_staff} "
                f"week commencing {pd.to_datetime(week_commencing).date()}"
            )

            st.rerun()   # ← force immediate refresh

    with tab3:

        st.title("📅 Weekly On-Site Planner")

        # ------------------------------------------------
        # Load staff names (active only)
        # ------------------------------------------------
        staff_names = (
            st.session_state.staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"]
            .sort_values()
            .tolist()
        )

        # ------------------------------------------------
        # Select Staff Member to Edit
        # ------------------------------------------------
        st.subheader("✏️ Add or Edit On-Site Days for a Specific Team Member")

        selected_staff_os = st.selectbox("Select On-site Team Member", staff_names, index=None)

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
            pf.save_on_site(
                staff_member=selected_staff,
                week_commencing=week_commencing,
                on_site_days=on_site_days
            )

            st.success(
                f"On-Site saved for {selected_staff} "
                f"week commencing {pd.to_datetime(week_commencing).date()}"
            )

            st.rerun()   # ← force immediate refresh

    with tab4:

        st.title("📅 Programme Overview")

        st.set_page_config(layout="wide")
        # ------------------------------------------------
        # Weekly Leave Calendar
        # ------------------------------------------------
        st.subheader("📊 Team Leave Calendar View (Weekly Heatmap)")

        leave_df = pf.filter_by_access(leave_calendar_df)

        pivot = leave_df.pivot_table(
            index="staff_member",
            columns="week_number",
            values="days_leave",
            fill_value=0
        )

        # Manual gradient colouring without matplotlib
        # def cell_color(val):
        #     # Scale 0–5 days (feel free to adjust)
        #     max_days = 5
        #     intensity = min(val / max_days, 1)
        #     r = int(255 * intensity)
        #     g = int(200 * (1 - intensity))
        #     b = 0
        #     return f"background-color: rgb({r}, {g}, {b})"
        
        def cell_color(val):
            # Scale 0–5 days (feel free to adjust)
            max_days = 5
            intensity = min(val / max_days, 1)
            r = int(255 * intensity)
            g = int(200 * (1 - intensity))
            b = 0
            return f"background-color: rgb({r}, {g}, {b}); color: rgb({r}, {g}, {b});"

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

        onsite_df = pf.filter_by_access(onsite_calendar_df)

        pivot = onsite_df.pivot_table(
            index="staff_member",
            columns="week_number",
            values="on_site_days",
            fill_value=0
        )

        # Manual gradient colouring without matplotlib
        # def cell_color(val):
        #     # Scale 0–5 days (feel free to adjust)
        #     max_days = 5
        #     intensity = min(val / max_days, 1)
        #     r = 0
        #     g = int(200 * (1 - intensity))
        #     b = int(255 * intensity)
        #     return f"background-color: rgb({r}, {g}, {b})"
        
        def cell_color(val):
            # Scale 0–5 days (feel free to adjust)
            max_days = 5
            intensity = min(val / max_days, 1)
            r = 0
            g = int(200 * (1 - intensity))
            b = int(255 * intensity)
            return f"background-color: rgb({r}, {g}, {b}); color: rgb({r}, {g}, {b});"

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

        prog_df = pf.filter_by_access(st.session_state.programme_calendar_df)

        fig = pf.make_activity_chart(prog_df, programme_names)
        
        fig.update_layout(
                        width=1200,
                        height=1200
                        )
        
        st.plotly_chart(fig, use_container_width=True)

        


