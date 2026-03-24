import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
#import numpy as np
# bring in data from data store
import data_store as ds

# Check if another page signaled a data refresh
ds.handle_trigger_reload()

# Normal initial load (first run)
if "staff_prog_monthly_df" not in st.session_state:
    ds.load_or_refresh_all()
    
#import numpy as np
import planner_functions as pf
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  # convenient for month offsets

max_days = 5
steps = 50

def dashboard():

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("📊 Capacity Dashboard")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        st.write("Email: info@gettingitrightfirsttime.co.uk")

    st.divider()

    # Handle any cross‑page reload triggers first
    ds.handle_trigger_reload()
    # Ensure everything is loaded (initial only)
    if "staff_prog_monthly_df" not in st.session_state:
        ds.load_or_refresh_all()

    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df
    programme_activity_df = st.session_state.programme_calendar_df
    staff_prog_monthly_df = st.session_state.staff_prog_monthly_df

    #st.write(leave_calendar_df)

    # Ensure dates are proper datetime
    programme_activity_df["week_commencing"] = pd.to_datetime(
        programme_activity_df["week_commencing"],
        dayfirst=True,
        errors="coerce"
    )

    # Month from the Monday date
    programme_activity_df["month"] = programme_activity_df["week_commencing"].dt.to_period("M").dt.to_timestamp()

    #st.write(programme_activity_df)
    
    # Rename for clarity
    programme_list_df = st.session_state.programme_list
    # Join programme_activity_df with lookup on the correct column name
    merged_df = programme_activity_df.merge(
        programme_list_df[["programme_categories", "programme_group"]],
        how="left",
        left_on="programme_category",      # your activity df column
        right_on="programme_categories"    # lookup df column
        )
    # get rid of programme_category column
    merged_df.drop(columns="programme_category", inplace=True)
    # Replace programme_category with programme_group for the pivot
    pivot = (
        merged_df
        .pivot_table(
            index="month",
            columns="programme_group",     # <-- now using group instead of category
            values="activity_value",
            aggfunc="sum",
            fill_value=0
        )
        .sort_index()
        .reset_index()
    )

    # ---------------------------
    # Monthly Capacity / Utilisation Chart
    # ---------------------------
    dfm = staff_prog_monthly_df

    if dfm is None or dfm.empty:
        st.info("No monthly capacity data available yet.")
        return

    # Ensure month is datetime
    dfm["month"] = pd.to_datetime(dfm["month"], errors="coerce")
    dfm = dfm.dropna(subset=["month"]).sort_values("month").reset_index(drop=True)

    # Default: last 12 months in the data (or fewer if not available)
    #dfm = dfm.tail(12).copy()
    dfm["month_label"] = dfm["month"].dt.strftime("%b-%Y")

    st.subheader("👥 Staff Utilisation")

    fig = go.Figure()

    # --- Available Hours (yellow line, Y1 axis) ---
    fig.add_trace(
        go.Scatter(
            x=dfm["month_label"],
            y=dfm["total_avail_hours"],
            name="Actual Capacity (Hours)",
            mode="lines",
            line=dict(color="yellow"),
            yaxis="y1"
        )
    )

    # --- Total Capacity (green line, Y1 axis) ---
    fig.add_trace(
        go.Scatter(
            x=dfm["month_label"],
            y=dfm["total_contr_hours"],
            name="Total Capacity (Hours)",
            mode="lines",
            line=dict(color="limegreen"),
            yaxis="y1"
        )
    )

    # --- Utilisation Rate (darkblue dashed line, Y2 axis) ---
    fig.add_trace(
        go.Scatter(
            x=dfm["month_label"],
            y=dfm["util_rate"],
            name="Utilisation Rate (%)",
            yaxis="y2",
            mode="lines",
            line=dict(color="blue", dash="dash", width=2)
        )
    )

    # --- Utilisation Hours (bar chart, Y1 axis, NHS Blue) ---
    fig.add_trace(
        go.Bar(
            x=dfm["month_label"],
            y=dfm["total_util_hours"],
            name="Utilisation Hours",
            yaxis="y1",
            opacity=0.8,
            marker_color="dodgerblue" #"003f7f"
        )
    )

    # --- Utilisation Target (red dashed line, Y2 axis) ---
    if "util_target" in dfm.columns:
        fig.add_trace(
            go.Scatter(
                x=dfm["month_label"],
                y=dfm["util_target"],
                name="Utilisation Target",
                mode="lines",
                line=dict(color="red", dash="dash", width=2),
                yaxis="y2"
            )
        )

    fig.update_layout(
        xaxis=dict(
            title="Month",
            type="category",
            tickangle=-45
        ),
        yaxis=dict(
            title="Hours",
            side="left",
            showgrid=False
        ),
        yaxis2=dict(
            title="Utilisation Rate (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, 150]
        ),
        barmode="overlay",
        legend=dict(
            orientation="v",
            xanchor="left",
            x=0.01,
            yanchor="bottom",
            y=0.02,
            bgcolor="rgba(255,255,255,0.6)",
            bordercolor="gray",
            borderwidth=1
        ),
        margin=dict(b=80, t=80),
        height=600
    )


    st.plotly_chart(fig, width='stretch')

    # ------------------------------------------------
    # Monthly Programme Activity Stacked Area Chart
    # ------------------------------------------------

    st.divider()

    st.subheader("🧩 Programme Activity")

    category_cols = [col for col in pivot.columns if col != "month"]
    num_categories = len(category_cols)
    colorscale = px.colors.sequential.Viridis
    # Evenly sample colors from scale
    color_sequence = pc.sample_colorscale(
        colorscale,
        [i / max(1, (num_categories - 1)) for i in range(num_categories)]
    )
    # Helper to convert 'rgb(r,g,b)' → 'rgba(r,g,b,a)'
    def rgb_to_rgba(rgb_str, alpha=0.6):
        rgb_values = rgb_str.strip("rgb()").split(",")
        return f"rgba({rgb_values[0]},{rgb_values[1]},{rgb_values[2]},{alpha})"
    fig2 = go.Figure()
    for i, col in enumerate(category_cols):
        rgb_color = color_sequence[i]
        rgba_color = rgb_to_rgba(rgb_color, alpha=0.6)
        fig2.add_trace(
            go.Scatter(
                x=pivot["month"],
                y=pivot[col],
                mode="lines",
                stackgroup="one",
                name=col,
                line=dict(color=rgb_color, width=2),
                fillcolor=rgba_color  # now valid RGBA string
            )
        )
    fig2.update_layout(
        xaxis_title="Month",
        yaxis_title="Total Activity (Hours)",
        hovermode="x unified",
        height=600,
        template="plotly_white"
    )
    st.plotly_chart(fig2, width='stretch')     

    # ------------------------------------------------
    # Weekly Leave, Booked-Out and Combined Heatmaps
    # ------------------------------------------------

    ##### Code to test different heatmap colors #####
    
    st.subheader("🎨 Heatmap Color Options")
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
    # Allow the user to pick one
    selected_name = st.radio("Select a colorscale to preview:", list(color_options.keys()))
    # Show preview bar
    st.plotly_chart(
        pf.preview_colorscale(color_options[selected_name], title=selected_name),
        width='stretch'
    )

    ##########

    MAX_DAYS = 5
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    # Radio Button selector
    view_option = st.radio(
        "Select View:",
        ["✈️ Leave Heatmap", "🗓️ Planner Heatmap", "🔀 Combined Heatmap"],
        horizontal=True
    )
    # Filter data to show 6 months back 6 months forward
    # Define 6 months backward and forward window
    today = date.today()
    window_start = pd.Timestamp(today - relativedelta(months=6))
    window_end = pd.Timestamp(today + relativedelta(months=6))
    # ------------------------------------------------
    # Load and filter data
    # ------------------------------------------------
    leave_df = pf.filter_by_access(leave_calendar_df).copy()
    
    onsite_df = pf.filter_by_access(onsite_calendar_df).copy()
    leave_df["week_commencing"] = pd.to_datetime(leave_df["week_commencing"], errors="coerce")
    onsite_df["week_commencing"] = pd.to_datetime(onsite_df["week_commencing"], errors="coerce")
    # Apply 12‑month rolling (6 months back, 6 months ahead)
    leave_df = leave_df[
        (leave_df["week_commencing"] >= window_start) &
        (leave_df["week_commencing"] <= window_end)
    ]
    #st.write(leave_df)
    onsite_df = onsite_df[
        (onsite_df["week_commencing"] >= window_start) &
        (onsite_df["week_commencing"] <= window_end)
    ]

    # ------------------------------------------------
    # Build combined dataset after filtering
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
    combined_df["total_days"] = combined_df["days_leave"] + combined_df["on_site_days"]

    st.subheader("👥 Staff Availability - Heatmap")

    # View selector logic
    if view_option == "✈️ Leave Heatmap":
        st.subheader("✈️ Leave")
        leave_colors = [[0.0, "rgb(0,200,0)"], [1.0, "rgb(255,0,0)"]]
        fig = pf.create_52week_heatmap(
            leave_df,
            value_col="days_leave",
            title="Leave",
            colorscale=color_options[selected_name],
            colorbar_title="Days of Leave",
            zmax=MAX_DAYS,
            highlight_current_week=True
        )
        st.plotly_chart(fig, width='stretch')
    elif view_option == "🗓️ Planner Heatmap":
        st.subheader("🗓️ Planner")
        planner_colors = [[0.0, "rgb(0,200,0)"], [1.0, "rgb(0,0,255)"]]
        fig = pf.create_52week_heatmap(
            onsite_df,
            value_col="on_site_days",
            title="Planner",
            colorscale=color_options[selected_name],
            colorbar_title="Days Booked Out",
            zmax=MAX_DAYS,
            highlight_current_week=True
            
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.subheader("🔀 Combined")
        combined_colors = [[0.0, "rgb(150,255,150)"], [1.0, "rgb(255,100,0)"]]
        fig = pf.create_52week_heatmap(
            combined_df,
            value_col="total_days",
            title="Combined",
            colorscale=color_options[selected_name],
            colorbar_title="Total Days (Leave + Planner)",
            zmax=MAX_DAYS,
            highlight_current_week=True
        )
        st.plotly_chart(fig, width='stretch')