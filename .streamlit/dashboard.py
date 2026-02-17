import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
#import numpy as np
# bring in data from data store
import data_store as ds
#import numpy as np
import planner_functions as pf
from datetime import date, timedelta

max_days = 5
steps = 50

def dashboard():

    st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)

    st.title("📊 Mental Health GIRFT - Capacity Dashboard")

    st.divider()

    # Ensure everything is loaded
    if "staff_prog_monthly_df" not in st.session_state:
        ds.load_or_refresh_all()

    leave_calendar_df = st.session_state.leave_calendar_df
    onsite_calendar_df = st.session_state.onsite_calendar_df
    programme_activity_df = st.session_state.programme_calendar_df
    staff_prog_monthly_df = st.session_state.staff_prog_monthly_df

    # Ensure dates are proper datetime
    programme_activity_df["week_commencing"] = pd.to_datetime(
        programme_activity_df["week_commencing"],
        dayfirst=True,
        errors="coerce"
    )

    # Month from the Monday date
    programme_activity_df["month"] = programme_activity_df["week_commencing"].dt.to_period("M").dt.to_timestamp()

    #st.write(programme_activity_df)
    
    pivot = (
            programme_activity_df
            .pivot_table(
                index="month",
                columns="programme_category",
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


    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------
    # Weekly Programme Activity Stacked Area Chart
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
    st.plotly_chart(fig2, use_container_width=True)     


    # ------------------------------------------------
    # Weekly Leave Calendar Heatmap (keep weekly)
    # ------------------------------------------------
    
    st.divider()
    
    st.subheader("✈️ Leave - Heatmap")

    MAX_DAYS = 5

    # Figure out current week start (assume Monday)
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())

    leave_df = pf.filter_by_access(leave_calendar_df).copy()
    leave_df["week_commencing"] = pd.to_datetime(leave_df["week_commencing"], errors="coerce")

    # Match roughly same span as the monthly chart: from first month shown to after last month
    start_date = dfm["month"].min()
    end_date = (dfm["month"].max() + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1))

    leave_df_span = leave_df[
        (leave_df["week_commencing"] >= start_date) &
        (leave_df["week_commencing"] < end_date)
    ].copy()

    pivot = leave_df_span.pivot_table(
        index="staff_member",
        columns="week_commencing",
        values="days_leave",
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
            ticktext.append(c.strftime("%d-%b-%y"))  # 👈 include year
            if c_date == current_week_start:
                current_idx = i
        else:
            ticktext.append(str(c))

        if c_date == current_week_start:
            current_idx = i

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
                    "Week Commencing: %{customdata}<br>"
                    "Days Leave: %{z:.1f}<extra></extra>"
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
        yaxis=dict(automargin=True),
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
            layer="below",
        )

    st.plotly_chart(fig_leave, use_container_width=True)

    # ------------------------------------------------
    # Weekly On-Site Calendar
    # ------------------------------------------------
    
    st.divider()
    
    st.subheader("🗓️ Planner - Heatmap")

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
            ticktext.append(c.strftime("%d-%b-%y"))  # 👈 include year
            if c_date == current_week_start:
                current_idx = i
        else:
            ticktext.append(str(c))

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
            colorbar=dict(title="Days Booked Out"),
            zmin=0,
            zmax=MAX_DAYS,
            hovertemplate=(
                                "Staff: %{y}<br>"
                                "Week Commencing: %{customdata}<br>"
                                "Days On-Site: %{z:.1f}<extra></extra>"
                            ),
customdata=[[c.strftime("%d-%b-%y") for c in cols]] * len(y),
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