import streamlit as st
import pandas as pd
import plotly.graph_objects as go
#import plotly.express as px
#import plotly.colors as pc
#import numpy as np
# bring in data from data store
import data_store as ds
import planner_functions as pf

# Check if another page signaled a data refresh
pf.handle_trigger_reload()

# Normal initial load (first run)
if "staff_detail_monthly_df" not in st.session_state:
    ds.load_or_refresh_all()
    
#import numpy as np
import planner_functions as pf
#from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  # convenient for month offsets

max_days = 5
steps = 50

def staff_dashboard():

    st.set_page_config(layout="wide")

    logged_in_staff = st.session_state.get("staff_member")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header(f"📊 Your Capacity Dashboard: {logged_in_staff}")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        #st.write("Email: info@gettingitrightfirsttime.co.uk")

    st.divider()

    # Handle any cross‑page reload triggers first
    pf.handle_trigger_reload()
    # Ensure everything is loaded (initial only)
    if "staff_detail_monthly_df" not in st.session_state:
        ds.load_or_refresh_all()

    staff_detail_monthly_df = st.session_state.staff_detail_monthly_df

    # ---------------------------
    # Monthly Capacity / Utilisation Chart
    # ---------------------------
    dfm = staff_detail_monthly_df

    # filter to only the logged in user
    dfm = dfm[dfm["staff_member"] == logged_in_staff]

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
            name="Deployable (Hours)",
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
            name="Contracted (Hours)",
            mode="lines",
            line=dict(color="limegreen"),
            yaxis="y1"
        )
    )

    # --- Utilisation Rate (darkblue dashed line, Y2 axis) ---
    # fig.add_trace(
    #     go.Scatter(
    #         x=dfm["month_label"],
    #         y=dfm["util_rate"],
    #         name="Utilisation Rate (%)",
    #         yaxis="y2",
    #         mode="lines",
    #         line=dict(color="blue", dash="dash", width=2)
    #     )
    # )

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
    # if "util_target" in dfm.columns:
    #     fig.add_trace(
    #         go.Scatter(
    #             x=dfm["month_label"],
    #             y=dfm["util_target"],
    #             name="Utilisation Target",
    #             mode="lines",
    #             line=dict(color="red", dash="dash", width=2),
    #             yaxis="y2"
    #         )
    #     )

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
        # yaxis2=dict(
        #     title="Utilisation Rate (%)",
        #     overlaying="y",
        #     side="right",
        #     showgrid=False,
        #     range=[0, 150]
        # ),
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