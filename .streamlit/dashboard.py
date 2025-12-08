import streamlit as st
import pandas as pd
import plotly.graph_objects as go
# bring in data from data store
import data_store as ds

def dashboard():

    st.title("MHIST Capacity Dashboard")

    # df = pd.DataFrame(data)

    # # convert leave days to hours ready to compare with contracted hours
    # ds.leave_calendar_df['leave_hours'] = ds.leave_calendar_df['days_leave']*7.5

    # # merge leave calendar with staff list
    # ds.staff_leave_merged_df = ds.leave_calendar_df.merge(
    #     ds.staff_list,
    #     on="staff_member",
    #     how="left"     # or "inner" if you only want matching rows
    # )

    # # calculate amount of available staff
    # ds.staff_leave_merged_df['avail_hours'] = ds.staff_leave_merged_df['hours_pw']-ds.staff_leave_merged_df['leave_hours']

    # # merge programme calendar with staff list
    # ds.staff_prog_merged_df = ds.programme_calendar_df.merge(
    #     ds.staff_list,
    #     on="staff_member",
    #     how="left"     # or "inner" if you only want matching rows
    # )

    # ds.staff_leave_df = ds.leave_calendar_df[['staff_member','week_number','leave_hours']]

    # # add in leave from leave calendar
    # ds.staff_prog_combined_df = ds.staff_prog_merged_df.merge(
    #     ds.staff_leave_df,
    #     on=["staff_member","week_number"],
    #     how="left"     # or "inner" if you only want matching rows
    # )

    # # calculate amount of available staff
    # ds.staff_prog_combined_df['avail_hours'] = ds.staff_prog_combined_df['hours_pw']-ds.staff_prog_combined_df['leave_hours']

    # # calculate amount of available staff
    # ds.staff_prog_combined_df['non-deployable hours'] = ds.staff_prog_combined_df['avail_hours']*(1-ds.staff_prog_combined_df['deploy_ratio'])

    ds.load_or_refresh_all()
    
    # st.write(programme_calendar_df)

    staff_avail_grouped = ds.staff_prog_combined_df.groupby("week_number").agg(
        total_hours=("hours_pw", "sum"),
        available_hours=("avail_hours", "sum")  # or mean if it varies
    ).reset_index()

    #ds.programme_calendar_df['total_act_hours'] = ds.programme_calendar_df[ds.programme_names].sum(axis=1)

    staff_act_grouped = ds.programme_calendar_df.groupby("week_number").agg(
        total_act_hours=("total_act_hours", "sum")
        #available_hours=("avail_hours", "sum")  # or mean if it varies
        ).reset_index()
    
    # st.write(staff_act_grouped)

    # Create figure
    fig = go.Figure()
   
    # Add line for available hours
    fig.add_trace(
        go.Scatter(
            x=staff_avail_grouped["week_number"],
            y=staff_avail_grouped["available_hours"],
            name="Available Hours",
            mode="lines+markers",
            marker_color="red",
            yaxis="y1"
        )
    )

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

    # Update layout
    fig.update_layout(
        title="Available Hours vs Total Activity Hours",
        xaxis_title="Week",
        yaxis_title="Hours",
        barmode="overlay",  # or "group" if you prefer
        template="plotly_white",
        height=800
    )

    st.plotly_chart(fig, use_container_width=True)




