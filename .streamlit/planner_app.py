import streamlit as st
from streamlit import components
import pandas as pd
import os
import planner_functions as pf
import data_store as ds
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")

max_days = 5
steps = 50

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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Programme of Work","Scheduled Activity","Annual Leave","On-Site","All Activity"])

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
        st.title("📆 Scheduled Activity")
        st.subheader("⏱ Schedule Repeating Programme Activity for a Team Member")

        # ---------------------------
        # 1️⃣ Load active staff
        # ---------------------------
        staff_names = staff_list.loc[
            staff_list["archive_flag"] == 0, "staff_member"
        ].sort_values().tolist()

        selected_staff = st.selectbox(
            "Select Programme Team Member",
            staff_names,
            index=None,
            placeholder="Choose a staff member..."
        )

        # ---------------------------
        # 2️⃣ Load active programme categories (no archived)
        # ---------------------------
        active_programmes = programme_list.loc[
            programme_list["archive_flag"] == 0
        ].copy()

        programme_categories = sorted(
            active_programmes["programme_categories"].dropna().tolist()
        )

        selected_programme_category = st.selectbox(
            "Select Programme Category",
            programme_categories,
            index=None,
            placeholder="Choose a programme category..."
        )

        # ---------------------------
        # 3️⃣ Start week (week commencing)
        # ---------------------------
        week_commencing = st.date_input(
            "Select Start Week (Week Commencing / Monday)",
            help="This is the first Monday of the schedule.",
        )

        if week_commencing.weekday() != 0:
            st.warning("⚠️ The week commencing date should be a Monday.")

        # ---------------------------
        # 4️⃣ Number of weeks & hours per week
        # ---------------------------
        num_weeks = st.number_input(
            "Number of Weeks to Schedule",
            min_value=1,
            max_value=104,
            value=4,
            step=1,
            help="How many consecutive weeks to apply this activity for."
        )

        # 0 → 37.5 hours in 0.5 steps
        hour_values = [x * 0.5 for x in range(0, 76)]

        hours_per_week = st.selectbox(
            "Hours per Week",
            hour_values,
            index=hour_values.index(0.0),
            help="Scheduled hours per week for this programme category."
        )

        # ---------------------------
        # 5️⃣ Save button
        # ---------------------------
        if st.button("💾 Schedule Programme Activity"):
            if not selected_staff:
                st.error("Please select a staff member.")
            elif not selected_programme_category:
                st.error("Please select a programme category.")
            else:
                start_week = pd.to_datetime(week_commencing)

                # Loop over each week and update programme_activity in SQLite
                for week_offset in range(int(num_weeks)):
                    this_week = start_week + pd.Timedelta(weeks=week_offset)

                    # Build the activity_inputs dict expected by pf.save_programme_activity
                    activity_inputs = {
                        selected_programme_category: float(hours_per_week)
                    }

                    pf.save_programme_activity(
                        selected_staff=selected_staff,
                        week_commencing=this_week,
                        activity_inputs=activity_inputs,
                    )

                st.success(
                    f"Scheduled {hours_per_week} hours/week of "
                    f"**{selected_programme_category}** for **{selected_staff}** "
                    f"over {num_weeks} week(s) starting "
                    f"week commencing {start_week.date()}."
                )

                st.rerun()

    
    with tab3:

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

    with tab4:

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

    with tab5:

        st.title("📅 Programme Overview")

        from datetime import date, timedelta
        import numpy as np

        MAX_DAYS = 5
        KEY_STEPS = 100

        # Helper functions for keys
        def leave_rgb(val: float) -> str:
            t = min(max(val / MAX_DAYS, 0), 1)
            r = int(255 * t)
            g = int(200 * (1 - t))
            return f"rgb({r},{g},0)"

        def onsite_rgb(val: float) -> str:
            t = min(max(val / MAX_DAYS, 0), 1)
            r = 0
            g = int(200 * (1 - t))
            b = int(255 * t)
            return f"rgb({r},{g},{b})"

        # Figure out current week start (assume Monday)
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # ------------------------------------------------
        # Weekly Leave Calendar
        # ------------------------------------------------
        st.subheader("📊 Team Leave Calendar View (Weekly Heatmap)")

        leave_df = pf.filter_by_access(leave_calendar_df)

        start_date = pd.Timestamp("2025-01-01")
        end_date   = start_date + pd.DateOffset(years=1)   # 12 months window

        leave_df_12m = leave_df[
            (leave_df["week_commencing"] >= start_date) &
            (leave_df["week_commencing"] < end_date)
        ]

        pivot = leave_df_12m.pivot_table(
            index="staff_member",
            columns="week_commencing",
            values="days_leave",
            fill_value=0
        )

        # Data for Plotly
        z = pivot.to_numpy()
        y = pivot.index.astype(str).tolist()
        cols = list(pivot.columns)

        # Use numeric x positions so we can highlight a full column
        x_vals = list(range(len(cols)))
        ticktext = []
        current_idx = None

        for i, c in enumerate(cols):
            # c might be Timestamp, datetime.date, etc.
            if hasattr(c, "date"):
                c_date = c.date()
                label = c.strftime("%d-%b")
            elif isinstance(c, date):
                c_date = c
                label = c.strftime("%d-%b")
            else:
                c_date = None
                label = str(c)

            ticktext.append(label)

            if c_date == current_week_start:
                current_idx = i

        # Leave heatmap: green -> red
        leave_colorscale = [
            [0.0, "rgb(0,200,0)"],   # 0 days
            [1.0, "rgb(255,0,0)"],   # max days
        ]

        fig_leave = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x_vals,
                y=y,
                colorscale=leave_colorscale,
                colorbar=dict(title="Days of Leave"),
                zmin=0,
                zmax=MAX_DAYS,
                hovertemplate=(
                    "Staff: %{y}<br>"
                    "Week: %{x}<br>"
                    "Days leave: %{z:.2f}<extra></extra>"
                ),
            )
        )

        fig_leave.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=x_vals,
                ticktext=ticktext,
                tickangle=90,
            ),
            yaxis=dict(
                automargin=True,
            ),
            margin=dict(l=160, r=20, t=40, b=120),
            height=max(350, pivot.shape[0] * 20 + 160),
            showlegend=False

        )

        # Highlight current week column if present
        if current_idx is not None:
            fig_leave.add_vrect(
                x0=current_idx - 0.5,
                x1=current_idx + 0.5,
                xref="x",
                yref="paper",
                fillcolor="rgba(0,0,0,0.12)",
                opacity=0.15,
                line_width=2,
                line_color="black",
                layer="below",  # keep heatmap cells visible
            )

        fig_leave.update_layout(showlegend=False)

        st.plotly_chart(fig_leave, use_container_width=True)

        # Horizontal key at bottom
        st.markdown("**Key (Days of Leave)**")

        gradient = ", ".join(
            [leave_rgb(v) for v in np.linspace(0, MAX_DAYS, KEY_STEPS)]
        )

        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; margin-top:10px; margin-bottom:35px;">
                <div style="
                    background: linear-gradient(to right, {gradient});
                    height: 20px;
                    width: 300px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                "></div>
                <div>0 → {MAX_DAYS} days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ------------------------------------------------
        # Weekly On-Site Calendar
        # ------------------------------------------------
        st.subheader("📊 Team On-Site View (Weekly Heatmap)")

        onsite_df = pf.filter_by_access(onsite_calendar_df)

        pivot = onsite_df.pivot_table(
            index="staff_member",
            columns="week_commencing",
            values="on_site_days",
            fill_value=0
        )

        z = pivot.to_numpy()
        y = pivot.index.astype(str).tolist()
        cols = list(pivot.columns)

        x_vals = list(range(len(cols)))
        ticktext = []
        current_idx = None

        for i, c in enumerate(cols):
            if hasattr(c, "date"):
                c_date = c.date()
                label = c.strftime("%d-%b")
            elif isinstance(c, date):
                c_date = c
                label = c.strftime("%d-%b")
            else:
                c_date = None
                label = str(c)

            ticktext.append(label)

            if c_date == current_week_start:
                current_idx = i

        # On-site heatmap: green -> blue
        onsite_colorscale = [
            [0.0, "rgb(0,200,0)"],   # 0 days on site
            [1.0, "rgb(0,0,255)"],   # max days on site
        ]

        fig_onsite = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x_vals,
                y=y,
                colorscale=onsite_colorscale,
                colorbar=dict(title="Days on Site"),
                zmin=0,
                zmax=MAX_DAYS,
                hovertemplate=(
                    "Staff: %{y}<br>"
                    "Week: %{x}<br>"
                    "Days on site: %{z:.2f}<extra></extra>"
                ),
            )
        )

        fig_onsite.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=x_vals,
                ticktext=ticktext,
                tickangle=90,
            ),
            yaxis=dict(
                automargin=True,
            ),
            margin=dict(l=160, r=20, t=40, b=120),
            height=max(350, pivot.shape[0] * 20 + 160),
            showlegend=False

        )

        if current_idx is not None:
            fig_onsite.add_vrect(
                x0=current_idx - 0.5,
                x1=current_idx + 0.5,
                xref="x",
                yref="paper",
                fillcolor="rgba(0,0,0,0.12)",
                opacity=0.15,
                line_width=2,
                line_color="black",
                layer="below",
            )

        fig_onsite.update_layout(showlegend=False)


        st.plotly_chart(fig_onsite, use_container_width=True)

        st.markdown("**Key (Days On Site)**")

        gradient = ", ".join(
            [onsite_rgb(v) for v in np.linspace(0, MAX_DAYS, KEY_STEPS)]
        )

        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; margin-top:10px; margin-bottom:35px;">
                <div style="
                    background: linear-gradient(to right, {gradient});
                    height: 20px;
                    width: 300px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                "></div>
                <div>0 → {MAX_DAYS} days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # summary of weekly programme activity
        st.subheader("📊 Weekly Programme Activity Breakdown")

        prog_df = pf.filter_by_access(st.session_state.programme_calendar_df)

        fig = pf.make_activity_chart(prog_df, programme_names)
        
        fig.update_layout(
                        width=1200,
                        height=1200
                        )
        
        st.plotly_chart(fig, use_container_width=True)

        


