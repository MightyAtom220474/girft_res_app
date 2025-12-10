import streamlit as st
import pandas as pd
import plotly.graph_objects as go
# bring in data from data store
import data_store as ds

def dashboard():

    st.title("MHIST Capacity Dashboard")

    ds.load_or_refresh_all()
    
    fig = go.Figure()

    # --- Available Hours (yellow line, Y1 axis) ---
    fig.add_trace(
        go.Scatter(
            x=ds.staff_prog_pivot_df["week_number"],
            y=ds.staff_prog_pivot_df["total_avail_hours"],
            name="Hours",
            mode="lines",
            line=dict(color="yellow"),
            yaxis="y1"
        )
    )

    # --- Utilisation Rate (dashed-line, Y2 axis) ---
    fig.add_trace(
        go.Scatter(
            x=ds.staff_prog_pivot_df["week_number"],
            y=ds.staff_prog_pivot_df["util_rate"],
            name="Utilisation Rate (%)",
            yaxis="y2",
            mode="lines",
            line=dict(color="darkblue", dash="dash", width=2)
        )
    )

    # --- Utilisation Hours (bar chart, Y1 axis) ---
    fig.add_trace(
        go.Bar(
            x=ds.staff_prog_pivot_df["week_number"],
            y=ds.staff_prog_pivot_df["total_util_hours"],
            name="Utilisation Hours",
            yaxis="y1",
            opacity=0.8,
            marker_color="#003f7f" # NHS Blue
        )
    )

    # Utilisation Target (red dashed line)
    fig.add_trace(
        go.Scatter(
            x=ds.staff_prog_pivot_df["week_number"],
            y=ds.staff_prog_pivot_df["util_target"],   # must exist in your DF
            name="Utilisation Target (85%)",
            mode="lines",
            line=dict(color="red", dash="dash", width=2),
            yaxis="y2"
        )
    )

    # --- Layout: dual axes ---
    fig.update_layout(
        xaxis=dict(title="Week Number"),

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
        legend=dict(x=0.01, y=0.99)
    )

    st.plotly_chart(fig, use_container_width=True)

    #st.write(ds.staff_prog_pivot_df)




