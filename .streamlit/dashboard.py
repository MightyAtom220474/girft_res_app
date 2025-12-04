import streamlit as st
import pandas as pd
import plotly.graph_objects as go
# bring in data from Capacity Planner page
from planner_app import staff_leave_merged_df, activity_calendar_df, activity_names

st.title("MHIST Capacity Dashboard")

st.write(staff_leave_merged_df)

# df = pd.DataFrame(data)

staff_avail_grouped = staff_leave_merged_df.groupby("week_number").agg(
    total_hours=("hours_pw", "sum"),
    available_hours=("avail_hours", "sum")  # or mean if it varies
).reset_index()

activity_calendar_df['total_act_hours'] = activity_calendar_df[activity_names].sum(axis=1)

staff_act_grouped = activity_calendar_df.groupby("week_number").agg(
    total_hours=("total_act_hours", "sum")
    #available_hours=("avail_hours", "sum")  # or mean if it varies
).reset_index()

# Create figure
fig = go.Figure()

# Add histogram / bar for total hours
fig.add_trace(
    go.Bar(
        x=staff_act_grouped["week_number"],
        y=staff_act_grouped["total_act_hours"],
        name="Total Activity Hours",
        marker_color="lightblue",
        yaxis="y1"
    )
)

# Add line for available hours
fig.add_trace(
    go.Scatter(
        x=staff_avail_grouped["week"],
        y=staff_avail_grouped["avail_hours"],
        name="Available Hours",
        mode="lines+markers",
        marker_color="red",
        yaxis="y1"
    )
)

# Update layout
fig.update_layout(
    title="Available Hours vs Total Activity Hours",
    xaxis_title="Week",
    yaxis_title="Hours",
    barmode="overlay",  # or "group" if you prefer
    template="plotly_white",
    height=500
)

fig.show()




