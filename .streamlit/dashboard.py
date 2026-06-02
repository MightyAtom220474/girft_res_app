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
# INITIAL LOAD / TRIGGERS
# ============================================================
pf.handle_trigger_reload()


if (
    "staff_prog_monthly_df" not in st.session_state
    or st.session_state.staff_prog_monthly_df.empty
):
    ds.load_or_refresh_all()

# ============================================================
# DASHBOARD FUNCTION
# ============================================================
def dashboard():

    st.set_page_config(layout="wide")

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------
    col1, col2 = st.columns([3.8, 1.2])

    with col1:
        st.header("📊 Team Capacity Dashboard")

    with col2:
        st.image(
            "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg",
            width=300
        )

    st.divider()

    # --------------------------------------------------------
    # REFRESH HANDLER
    # --------------------------------------------------------
    pf.handle_trigger_reload()

    if "staff_prog_monthly_df" not in st.session_state:
        ds.load_or_refresh_all()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------
    leave_df = st.session_state.leave_calendar_df
    onsite_df = st.session_state.onsite_calendar_df
    programme_df = st.session_state.programme_calendar_df
    monthly_df = st.session_state.staff_prog_monthly_df

    # --------------------------------------------------------
    # DATE CLEANING
    # --------------------------------------------------------
    programme_df["week_commencing"] = pd.to_datetime(
        programme_df["week_commencing"],
        errors="coerce"
    )

    programme_df["month"] = programme_df["week_commencing"].dt.to_period("M").dt.to_timestamp()

    # --------------------------------------------------------
    # PROGRAMME MERGE + PIVOT
    # --------------------------------------------------------
    programme_list_df = st.session_state.programme_list

    merged_df = programme_df.merge(
        programme_list_df[["programme_categories", "programme_group"]],
        how="left",
        left_on="programme_category",
        right_on="programme_categories"
    )

    merged_df.drop(columns="programme_category", inplace=True)

    merged_df["programme_group"] = merged_df["programme_group"].apply(pf.clean_programme)

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

    # ========================================================
    # MONTHLY CAPACITY CHART
    # ========================================================
    st.subheader("👥 Staff Utilisation")

    if monthly_df is None or monthly_df.empty:
        st.info("No monthly capacity data available yet.")
        return
    
    
    # st.write("DEBUG monthly_df columns:", monthly_df.columns.tolist())
    # st.write("DEBUG monthly_df head:", monthly_df.head())


    monthly_df["month"] = pd.to_datetime(monthly_df["month"])
    monthly_df["month_label"] = monthly_df["month"].dt.strftime("%b-%Y")

    fig = go.Figure()

    # ---------------------------
    # PRIMARY AXIS (HOURS)
    # ---------------------------

    # Establishment
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["total_contr_hours"],
        name="Establishment (Hours)",
        mode="lines",
        line=dict(color="limegreen"),
        yaxis="y1"
    ))

    # Available capacity
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["total_avail_hours"],
        name="Deployable Capacity (Hours)",
        mode="lines",
        line=dict(color="gold"),
        yaxis="y1"
    ))

    # Utilisation hours (bars)
    fig.add_trace(go.Bar(
        x=monthly_df["month_label"],
        y=monthly_df["total_util_hours"],
        name="Utilisation Hours",
        marker_color="dodgerblue",
        opacity=0.8,
        yaxis="y1"
    ))

    # ---------------------------
    # SECONDARY AXIS (%)
    # ---------------------------

    # Utilisation %
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["util_rate"],
        name="Utilisation %",
        mode="lines",
        line=dict(color="blue", dash="dash", width=2),
        yaxis="y2"
    ))

    # Target %
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["util_target"],
        name="Target %",
        mode="lines",
        line=dict(color="red", dash="dot", width=2),
        yaxis="y2"
    ))

    # ---------------------------
    # LAYOUT (CRITICAL)
    # ---------------------------

    fig.update_layout(
        xaxis=dict(
            title="Month",
            type="category",
            tickangle=-45
        ),

        # Primary axis → HOURS
        yaxis=dict(
            title="Hours",
            side="left",
            showgrid=False
        ),

        # Secondary axis → %
        yaxis2=dict(
            title="Utilisation (%)",
            overlaying="y",   # ✅ THIS IS KEY
            side="right",
            range=[0, 150],   # matches your % scale
            showgrid=False
        ),

        barmode="overlay",

        legend=dict(
            orientation="v",
            x=0.01,
            y=0.01,
            bgcolor="rgba(255,255,255,0.6)"
        ),

        height=600
    )

    st.plotly_chart(fig, use_container_width=True)


    # ========================================================
    # PROGRAMME STACKED AREA
    # ========================================================
    st.divider()
    st.subheader("🧩 Programme Activity")

    category_cols = [c for c in pivot.columns if c != "month"]

    colorscale = px.colors.sequential.Viridis
    color_sequence = pc.sample_colorscale(
        colorscale,
        [i / max(1, len(category_cols)-1) for i in range(len(category_cols))]
    )

    def rgb_to_rgba(rgb, alpha=0.6):
        vals = rgb.strip("rgb()").split(",")
        return f"rgba({vals[0]},{vals[1]},{vals[2]},{alpha})"

    fig2 = go.Figure()

    for i, col in enumerate(category_cols):
        fig2.add_trace(go.Scatter(
            x=pivot["month"],
            y=pivot[col],
            stackgroup="one",
            name=col,
            line=dict(color=color_sequence[i]),
            fillcolor=rgb_to_rgba(color_sequence[i])
        ))

    fig2.update_layout(
        xaxis_title="Month",
        yaxis_title="Hours",
        height=600
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ========================================================
    # HEATMAPS
    # ========================================================
    # ------------------------------------------------
    # HEATMAPS WITH COLOR SELECTOR (FULL RESTORED)
    # ------------------------------------------------

    st.divider()

    st.subheader("🎨 Heatmap Color Options")

    # ------------------------------------------------
    # COLOR OPTIONS
    # ------------------------------------------------
    color_options = {
        "1️⃣ Traffic Light (Green → Yellow → Red)": [
            [0.0, "rgb(0, 200, 0)"], [0.5, "rgb(255, 255, 0)"], [1.0, "rgb(255, 0, 0)"]
        ],
        "2️⃣ Blue → Yellow → Orange": [
            [0.0, "rgb(0, 120, 255)"], [0.5, "rgb(255, 255, 150)"], [1.0, "rgb(255, 140, 0)"]
        ],
        "3️⃣ Light → Dark Blue": [
            [0.0, "rgb(230, 245, 255)"], [1.0, "rgb(0, 70, 140)"]
        ],
        "4️⃣ Viridis (Plotly Built‑in)": "Viridis",
        "5️⃣ Grey → Amber → Purple": [
            [0.0, "rgb(220, 220, 220)"], [0.5, "rgb(255, 180, 50)"], [1.0, "rgb(120, 0, 120)"]
        ]
    }

    # ------------------------------------------------
    # COLOR PICKER
    # ------------------------------------------------
    selected_name = st.radio(
        "Select a colorscale:",
        list(color_options.keys()),
        horizontal=True
    )

    # ------------------------------------------------
    # PREVIEW BAR
    # ------------------------------------------------
    st.plotly_chart(
        pf.preview_colorscale(
            color_options[selected_name],
            title=selected_name
        ),
        use_container_width=True
    )

    st.divider()

    # ------------------------------------------------
    # DATA PREP
    # ------------------------------------------------
    MAX_DAYS = 5

    leave_df = st.session_state.leave_calendar_df.copy()
    onsite_df = st.session_state.onsite_calendar_df.copy()

    # Ensure datetime consistency
    leave_df["week_commencing"] = pd.to_datetime(
        leave_df["week_commencing"], errors="coerce"
    )
    onsite_df["week_commencing"] = pd.to_datetime(
        onsite_df["week_commencing"], errors="coerce"
    )

    # ------------------------------------------------
    # COMBINED DATASET
    # ------------------------------------------------
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

    # ------------------------------------------------
    # VIEW SELECTOR
    # ------------------------------------------------
    st.subheader("👥 Staff Availability - Heatmap")

    view_option = st.radio(
        "Select View:",
        ["✈️ Leave Heatmap", "🗓️ Planner Heatmap", "🔀 Combined Heatmap"],
        horizontal=True
    )

    # ------------------------------------------------
    # RENDER HEATMAPS
    # ------------------------------------------------

    if view_option == "✈️ Leave Heatmap":
        st.subheader("✈️ Leave")

        fig = pf.create_52week_heatmap(
            leave_df,
            value_col="days_leave",
            title=None,
            colorscale=color_options[selected_name],
            colorbar_title="Days of Leave",
            zmax=MAX_DAYS,
            highlight_current_week=True
        )

        st.plotly_chart(fig, use_container_width=True)

    elif view_option == "🗓️ Planner Heatmap":
        st.subheader("🗓️ Planner")

        fig = pf.create_52week_heatmap(
            onsite_df,
            value_col="on_site_days",
            title=None,
            colorscale=color_options[selected_name],
            colorbar_title="Days Booked Out",
            zmax=MAX_DAYS,
            highlight_current_week=True
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.subheader("🔀 Combined")

        fig = pf.create_52week_heatmap(
            combined_df,
            value_col="total_days",
            title=None,
            colorscale=color_options[selected_name],
            colorbar_title="Total Days (Leave + Planner)",
            zmax=MAX_DAYS,
            highlight_current_week=True
        )

        st.plotly_chart(fig, use_container_width=True)