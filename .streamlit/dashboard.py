import streamlit as st
import pandas as pd
import plotly.graph_objects as go
# bring in data from data store
import data_store as ds
import numpy as np
import planner_functions as pf

max_days = 5
steps = 50

def dashboard():

    st.title("MHIST Capacity Dashboard")

    # Make sure everything is loaded
    if "staff_prog_pivot_df" not in st.session_state:
        ds.load_or_refresh_all()

    # Base dataframe
    df = st.session_state.staff_prog_pivot_df.copy()

    # Ensure week_commencing is datetime
    df["week_commencing"] = pd.to_datetime(df["week_commencing"])

    # Filter to 12-month window
    start_date = pd.Timestamp("2025-01-01")
    end_date   = start_date + pd.DateOffset(years=1)   # 12 months window

    df_12m = df[
        (df["week_commencing"] >= start_date) &
        (df["week_commencing"] < end_date)
    ].copy()

    # Store back in session if you still want it
    st.session_state.staff_prog_pivot_df_12m = df_12m

    # Nice short label for x-axis (e.g. 06-Jan)
    df_12m["week_label"] = df_12m["week_commencing"].dt.strftime("%d-%b")

    fig = go.Figure()

    # --- Available Hours (yellow line, Y1 axis) ---
    fig.add_trace(
        go.Scatter(
            x=df_12m["week_label"],
            y=df_12m["total_avail_hours"],
            name="Hours",
            mode="lines",
            line=dict(color="yellow"),
            yaxis="y1"
        )
    )

    # --- Utilisation Rate (dashed line, Y2 axis) ---
    fig.add_trace(
        go.Scatter(
            x=df_12m["week_label"],
            y=df_12m["util_rate"],
            name="Utilisation Rate (%)",
            yaxis="y2",
            mode="lines",
            line=dict(color="darkblue", dash="dash", width=2)
        )
    )

    # --- Utilisation Hours (bar chart, Y1 axis) ---
    fig.add_trace(
        go.Bar(
            x=df_12m["week_label"],
            y=df_12m["total_util_hours"],
            name="Utilisation Hours",
            yaxis="y1",
            opacity=0.8,
            marker_color="#003f7f"  # NHS Blue
            # width is now relative to category, default is fine
        )
    )

    # --- Utilisation Target (red dashed line, Y2 axis) ---
    fig.add_trace(
        go.Scatter(
            x=df_12m["week_label"],
            y=df_12m["util_target"],   # must exist in your DF
            name="Utilisation Target (85%)",
            mode="lines",
            line=dict(color="red", dash="dash", width=2),
            yaxis="y2"
        )
    )

    # --- Layout: dual axes ---
    fig.update_layout(
        xaxis=dict(
            title="Week Commencing",
            type="category",
            tickangle=-45  # tilt labels so they don't collide
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
            showgrid=False
        ),
        barmode="overlay",
        legend=dict(x=0.01, y=0.99),
        margin=dict(b=80),  # extra space for rotated labels
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)


    #st.write(st.session_state.staff_prog_pivot_df_12m)

    # # ------------------------------------------------
    # # Weekly Leave Calendar
    # # ------------------------------------------------
    # st.subheader("📊 Team Leave Calendar View (Weekly Heatmap)")

    # leave_df = pf.filter_by_access(leave_calendar_df)

    # start_date = pd.Timestamp("2025-01-01")
    # end_date   = start_date + pd.DateOffset(years=1)   # 12 months window

    # leave_df_12m = leave_df[
    #     (leave_df["week_commencing"] >= start_date) &
    #     (leave_df["week_commencing"] < end_date)
    # ]

    # pivot = leave_df_12m.pivot_table(
    #     index="staff_member",
    #     columns="week_commencing",
    #     values="days_leave",
    #     fill_value=0
    # )

    # # Data for Plotly
    # z = pivot.to_numpy()
    # y = pivot.index.astype(str).tolist()
    # cols = list(pivot.columns)

    # # Use numeric x positions so we can highlight a full column
    # x_vals = list(range(len(cols)))
    # ticktext = []
    # current_idx = None

    # for i, c in enumerate(cols):
    #     # c might be Timestamp, datetime.date, etc.
    #     if hasattr(c, "date"):
    #         c_date = c.date()
    #         label = c.strftime("%d-%b")
    #     elif isinstance(c, date):
    #         c_date = c
    #         label = c.strftime("%d-%b")
    #     else:
    #         c_date = None
    #         label = str(c)

    #     ticktext.append(label)

    #     if c_date == current_week_start:
    #         current_idx = i

    # # Leave heatmap: green -> red
    # leave_colorscale = [
    #     [0.0, "rgb(0,200,0)"],   # 0 days
    #     [1.0, "rgb(255,0,0)"],   # max days
    # ]

    # fig_leave = go.Figure(
    #     data=go.Heatmap(
    #         z=z,
    #         x=x_vals,
    #         y=y,
    #         colorscale=leave_colorscale,
    #         colorbar=dict(title="Days of Leave"),
    #         zmin=0,
    #         zmax=MAX_DAYS,
    #         hovertemplate=(
    #             "Staff: %{y}<br>"
    #             "Week: %{x}<br>"
    #             "Days leave: %{z:.2f}<extra></extra>"
    #         ),
    #     )
    # )

    # fig_leave.update_layout(
    #     xaxis=dict(
    #         tickmode="array",
    #         tickvals=x_vals,
    #         ticktext=ticktext,
    #         tickangle=90,
    #     ),
    #     yaxis=dict(
    #         automargin=True,
    #     ),
    #     margin=dict(l=160, r=20, t=40, b=120),
    #     height=max(350, pivot.shape[0] * 20 + 160),
    #     showlegend=False

    # )

    # # Highlight current week column if present
    # if current_idx is not None:
    #     fig_leave.add_vrect(
    #         x0=current_idx - 0.5,
    #         x1=current_idx + 0.5,
    #         xref="x",
    #         yref="paper",
    #         fillcolor="rgba(0,0,0,0.12)",
    #         opacity=0.15,
    #         line_width=2,
    #         line_color="black",
    #         layer="below",  # keep heatmap cells visible
    #     )

    # fig_leave.update_layout(showlegend=False)

    # st.plotly_chart(fig_leave, use_container_width=True)

    # # Horizontal key at bottom
    # st.markdown("**Key (Days of Leave)**")

    # gradient = ", ".join(
    #     [leave_rgb(v) for v in np.linspace(0, MAX_DAYS, KEY_STEPS)]
    # )

    # st.markdown(
    #     f"""
    #     <div style="display:flex; align-items:center; gap:10px; margin-top:10px; margin-bottom:35px;">
    #         <div style="
    #             background: linear-gradient(to right, {gradient});
    #             height: 20px;
    #             width: 300px;
    #             border: 1px solid #ccc;
    #             border-radius: 4px;
    #         "></div>
    #         <div>0 → {MAX_DAYS} days</div>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )




