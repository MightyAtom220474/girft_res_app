import streamlit as st
import pandas as pd
import planner_functions as pf
import data_store as ds
ds.handle_trigger_reload()

from datetime import date, timedelta
import time

today = date.today()
current_monday = today - timedelta(days=today.weekday() + 7)


def planner():

    if (
        "programme_list" not in st.session_state
        or st.session_state.get("trigger_reload") == "programme"
    ):
        ds.load_or_refresh_all()
        st.session_state["trigger_reload"] = None

    staff_list = st.session_state.staff_list
    programme_list = st.session_state.programme_list
    programme_calendar_df = st.session_state.programme_calendar_df

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("📅 Activity Recording")
    with col2:
        st.image(
            "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg",
            width=300
        )

    st.divider()
    st.subheader("✏️ Add or Edit Weekly Programme Activity")

    # ---------------------------
    # STAFF SELECTION
    # ---------------------------
    staff_names = staff_list.loc[
        staff_list["archive_flag"] == 0, "staff_member"
    ].sort_values().tolist()

    logged_in_user = st.session_state.get("username", None)
    default_index = 0

    if logged_in_user:
        row = staff_list.loc[staff_list["username"] == logged_in_user]
        if not row.empty:
            staff_name = row["staff_member"].iloc[0]
            if staff_name in staff_names:
                default_index = staff_names.index(staff_name)

    selected_staff = st.selectbox(
        "Select Programme Team Member",
        staff_names,
        index=default_index
    )

    # ---------------------------
    # STAFF INFO + DEFAULTS
    # ---------------------------
    default_programme = None
    default_group = None
    deployable_hours = 0

    if selected_staff:

        staff_info = staff_list.loc[
            staff_list["staff_member"] == selected_staff
        ].head(1)

        if not staff_info.empty:

            hours_pw = float(staff_info.iloc[0].get("hours_pw", 37.5) or 37.5)
            deploy_ratio = float(staff_info.iloc[0].get("deploy_ratio", 1.0) or 1.0)

            deployable_hours = hours_pw * deploy_ratio

            # NEW: use central function (source of truth)
            default_hours = pf.calculate_default_hours_for_staff(
                staff_list,
                selected_staff,
                pct=1.0  # full allocation baseline
            )

            default_programme = staff_info.iloc[0].get("default_programme", None)

            if default_programme:
                match = programme_list.loc[
                    programme_list["programme_categories"] == default_programme
                ]
                if not match.empty:
                    default_group = match.iloc[0]["programme_group"]

            c1, c2 = st.columns(2)
            with c1:
                st.success(f"Contracted hours: {hours_pw:.1f}")
            with c2:
                st.success(f"Deployable hours: {deployable_hours:.1f}")

    # ---------------------------
    # WEEK
    # ---------------------------
    week_commencing = st.date_input(
        "Select Week Commencing (Monday)",
        value=current_monday
    )

    # ---------------------------
    # PROGRAMME FILTER
    # ---------------------------
    active_programmes = programme_list.loc[
        programme_list["archive_flag"] == 0
    ].copy()

    programme_groups = ["All"] + sorted(
        active_programmes["programme_group"].dropna().unique().tolist()
    )

    default_group_index = (
        programme_groups.index(default_group)
        if default_group in programme_groups
        else 0
    )

    selected_group = st.selectbox(
        "Select Programme Group",
        programme_groups,
        index=default_group_index
    )

    if selected_group == "All":
        programmes_filtered = active_programmes
    else:
        programmes_filtered = active_programmes.loc[
            active_programmes["programme_group"] == selected_group
        ]

    programme_categories_filtered = programmes_filtered["programme_categories"].tolist()

    # ---------------------------
    # EXISTING ACTIVITY
    # ---------------------------
    mask = (
        (programme_calendar_df["staff_member"] == selected_staff) &
        (programme_calendar_df["week_commencing"] == pd.to_datetime(week_commencing))
    )

    existing_lookup = (
        programme_calendar_df.loc[mask]
        .set_index("programme_category")["activity_value"]
        .to_dict()
    )

    # ---------------------------
    # AUTO DEFAULT LOGIC
    # ---------------------------
    AUTO_ALLOC_PCT = 1.0

    st.write(f"### Editing: **{selected_staff}**")
    st.write(f"#### Week: **{week_commencing}**")

    hour_values = [x * 0.5 for x in range(0, 76)]
    activity_inputs = {}

    for programme in programme_categories_filtered:

        # 1. Existing data ALWAYS wins
        if programme in existing_lookup:
            default_value = float(existing_lookup[programme])

        # 2. Default programme gets allocation
        elif programme == default_programme:
            default_value = pf.calculate_default_hours_for_staff(
                staff_list,
                selected_staff,
                pct=AUTO_ALLOC_PCT
            )

        else:
            default_value = 0.0

        # snap to valid values
        if default_value not in hour_values:
            default_value = min(hour_values, key=lambda x: abs(x - default_value))

        pretty_name = programme.replace("_", " ").title()

        activity_inputs[programme] = st.selectbox(
            pretty_name,
            hour_values,
            index=hour_values.index(default_value),
            key=f"{selected_staff}_{week_commencing}_{programme}"
        )

    # ---------------------------
    # SAVE
    # ---------------------------
    if st.button("💾 Save Programme Activity Changes"):
        pf.save_programme_activity(
            selected_staff=selected_staff,
            week_commencing=week_commencing,
            activity_inputs=activity_inputs
        )

        success_box = st.empty()
        success_box.success(
            f"Saved for {selected_staff} "
            f"week commencing {pd.to_datetime(week_commencing).date()}"
        )

        time.sleep(3)
        success_box.empty()

        st.session_state["trigger_reload"] = "programme"
        st.rerun()