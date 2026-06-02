import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc

import data_store as ds
import planner_functions as pf

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


# ============================================================
# LOAD DATA SAFELY
# ============================================================
pf.handle_trigger_reload()

if (
    "staff_prog_monthly_df" not in st.session_state
    or st.session_state.staff_prog_monthly_df is None
    or st.session_state.staff_prog_monthly_df.empty
):
    ds.load_or_refresh_all()


# ============================================================
# DASHBOARD
# ============================================================
def dashboard():

    st.set_page_config(layout="wide")

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------
    col1, col2 = st.columns([4, 1])

    with col1:
        st.header("📊 Team Capacity Dashboard")

    with col2:
        st.image(
            "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg",
            width=300
        )

    st.divider()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------
    monthly_df = st.session_state.staff_prog_monthly_df
    programme_df = st.session_state.programme_calendar_df
    programme_list_df = st.session_state.programme_list
    leave_df = st.session_state.leave_calendar_df
    onsite_df = st.session_state.onsite_calendar_df

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------
    if "month" not in monthly_df.columns:
        st.error(f"Missing 'month' column: {monthly_df.columns.tolist()}")
        return

    # --------------------------------------------------------
    # DATE WINDOW (6 MONTHS BACK/FORWARD)
    # --------------------------------------------------------
    today = date.today()
    window_start = pd.Timestamp(today - relativedelta(months=6))
    window_end = pd.Timestamp(today + relativedelta(months=6))

    monthly_df["month"] = pd.to_datetime(monthly_df["month"])

    monthly_df = monthly_df[
        (monthly_df["month"] >= window_start) &
        (monthly_df["month"] <= window_end)
    ].copy()

    monthly_df = monthly_df.sort_values("month")

    monthly_df["month_label"] = monthly_df["month"].dt.strftime("%b-%Y")


    # ========================================================
    # UTILISATION CHART
    # ========================================================
    st.subheader("👥 Staff Utilisation")

    fig = go.Figure()

    # Primary axis (hours)
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["total_contr_hours"],
        name="Establishment (Hours)",
        line=dict(color="limegreen"),
        yaxis="y1"
    ))

    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["total_avail_hours"],
        name="Deployable Capacity",
        line=dict(color="gold"),
        yaxis="y1"
    ))

    fig.add_trace(go.Bar(
        x=monthly_df["month_label"],
        y=monthly_df["total_util_hours"],
        name="Utilisation Hours",
        marker_color="dodgerblue",
        yaxis="y1"
    ))

    # Secondary axis (%)
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["util_rate"],
        name="Util %",
        line=dict(color="blue", dash="dash"),
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["util_target"],
        name="Target %",
        line=dict(color="red", dash="dot"),
        yaxis="y2"
    ))

    fig.update_layout(
        xaxis=dict(type="category", tickangle=-45),
        yaxis=dict(title="Hours"),
        yaxis2=dict(
            title="Utilisation (%)",
            overlaying="y",
            side="right",
            range=[0, 150]
        ),
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

    # ========================================================
    # PROGRAMME ACTIVITY
    # ========================================================
    st.divider()
    st.subheader("🧩 Programme Activity")

    programme_df["week_commencing"] = pd.to_datetime(
        programme_df["week_commencing"], errors="coerce"
    )

    programme_df["month"] = (
        programme_df["week_commencing"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    merged_df = programme_df.merge(
        programme_list_df[["programme_categories", "programme_group"]],
        how="left",
        left_on="programme_category",
        right_on="programme_categories"
    )

    merged_df["programme_group"] = merged_df["programme_group"].apply(
        pf.clean_programme
    )

    # ✅ CRITICAL FIX
    merged_df["programme_group"] = merged_df["programme_group"].fillna("Unassigned")

    pivot = (
        merged_df
        .pivot_table(
            index="month",
            columns="programme_group",
            values="activity_value",
            aggfunc="sum",
            fill_value=0
        )
        .sort_index()
        .reset_index()
    )

    category_cols = [c for c in pivot.columns if c != "month"]

    colorscale = px.colors.sequential.Viridis
    color_sequence = pc.sample_colorscale(
        colorscale,
        [i / max(1, len(category_cols)-1) for i in range(len(category_cols))]
    )

    fig2 = go.Figure()

    for i, col in enumerate(category_cols):
        fig2.add_trace(go.Scatter(
            x=pivot["month"],
            y=pivot[col],
            stackgroup="one",
            name=col,
            line=dict(color=color_sequence[i])
        ))

    fig2.update_layout(height=500)

    st.plotly_chart(fig2, use_container_width=True)

    # ========================================================
    # HEATMAP COLOR SELECTOR
    # ========================================================
    st.divider()

    st.subheader("🎨 Heatmap Color Options")

    color_options = {
        "Traffic Light": [[0, "green"], [0.5, "yellow"], [1, "red"]],
        "Blue → Orange": [[0, "blue"], [0.5, "yellow"], [1, "orange"]],
        "Viridis": "Viridis",
    }

    selected = st.radio(
        "Select colorscale:",
        list(color_options.keys()),
        horizontal=True
    )

    st.plotly_chart(
        pf.preview_colorscale(color_options[selected]),
        use_container_width=True
    )

    # ========================================================
    # HEATMAP DATA
    # ========================================================
    MAX_DAYS = 5

    leave_df["week_commencing"] = pd.to_datetime(leave_df["week_commencing"])
    onsite_df["week_commencing"] = pd.to_datetime(onsite_df["week_commencing"])

    combined_df = (
        leave_df[["staff_member", "week_commencing", "days_leave"]]
        .merge(
            onsite_df[["staff_member", "week_commencing", "on_site_days"]],
            on=["staff_member", "week_commencing"],
            how="outer"
        )
        .fillna(0)
    )

    combined_df["total_days"] = (
        combined_df["days_leave"] + combined_df["on_site_days"]
    )

    st.subheader("👥 Staff Availability - Heatmap")

    view_option = st.radio(
        "Select View:",
        ["Leave", "Planner", "Combined"],
        horizontal=True
    )

    if view_option == "Leave":
        fig = pf.create_52week_heatmap(
            leave_df,
            value_col="days_leave",
            colorscale=color_options[selected],
            zmax=MAX_DAYS
        )

    elif view_option == "Planner":
        fig = pf.create_52week_heatmap(
            onsite_df,
            value_col="on_site_days",
            colorscale=color_options[selected],
            zmax=MAX_DAYS
        )

    else:
        fig = pf.create_52week_heatmap(
            combined_df,
            value_col="total_days",
            colorscale=color_options[selected],
            zmax=MAX_DAYS
        )

    st.plotly_chart(fig, use_container_width=True)