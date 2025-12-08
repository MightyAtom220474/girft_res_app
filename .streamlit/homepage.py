import streamlit as st
import data_store as ds
import planner_functions as pf

def homepage():

    ##### Load up all data from data stores if available #####
    if ds.staff_list is None:
        ds.staff_list = pf.load_data("staff_list.csv")

    if ds.programme_list is None:
        ds.programme_list = pf.load_data("programme_categories.csv")

    staff_names = ds.staff_list['staff_member'].to_list()
    staff_names.sort()

    ds.programme_names = ds.programme_list['programme_categories'].to_list()
    ds.programme_names.sort()
    
    if ds.programme_list is None:
        ds.programme_list = pf.load_data('programme_categories.csv')

    ds.programme_names = ds.programme_list['programme_categories'].to_list()
    ds.programme_names.sort()

    if ds.leave_calendar_df is None:
        ds.leave_calendar_df = pf.load_or_update_leave_file('annual_leave_calendar.csv'
                                                    ,staff_names,'days_leave')
    if ds.onsite_calendar_df is None:
        ds.onsite_calendar_df = pf.load_or_update_leave_file('on_site_calendar.csv'
                                                    ,staff_names,'on_site_days')
    if ds.programme_calendar_df is None:
        ds.programme_calendar_df = pf.load_or_update_planner_file('programme_calendar.csv'
                                                    ,staff_names,ds.programme_names)
        
    ##### combine data frames and create calculated fields #####

    # convert leave days to hours ready to compare with contracted hours
    ds.leave_calendar_df['leave_hours'] = ds.leave_calendar_df['days_leave']*7.5
    # total up all deployable hours
    ds.programme_calendar_df['total_act_hours'] = ds.programme_calendar_df[ds.programme_names].sum(axis=1)

    # merge leave calendar with staff list
    ds.staff_leave_merged_df = ds.leave_calendar_df.merge(
        ds.staff_list,
        on="staff_member",
        how="left"     # or "inner" if you only want matching rows
    )

    # calculate amount of available staff
    ds.staff_leave_merged_df['avail_hours'] = ds.staff_leave_merged_df['hours_pw']-ds.staff_leave_merged_df['leave_hours']

    # merge programme calendar with staff list
    ds.staff_prog_merged_df = ds.programme_calendar_df.merge(
        ds.staff_list,
        on="staff_member",
        how="left"     # or "inner" if you only want matching rows
    )

    ds.staff_leave_df = ds.leave_calendar_df[['staff_member','week_number','leave_hours']]

    # add in leave from leave calendar
    ds.staff_prog_combined_df = ds.staff_prog_merged_df.merge(
        ds.staff_leave_df,
        on=["staff_member","week_number"],
        how="left"     # or "inner" if you only want matching rows
    )

    # calculate amount of available staff
    ds.staff_prog_combined_df['avail_hours'] = ds.staff_prog_combined_df['hours_pw']-ds.staff_prog_combined_df['leave_hours']

    # calculate amount of available staff
    ds.staff_prog_combined_df['non-deployable hours'] = ds.staff_prog_combined_df['avail_hours']*(1-ds.staff_prog_combined_df['deploy_ratio'])

    #print(leave_calendar_df)

    st.logo("https://lancsvp.org.uk/wp-content/uploads/2021/08/nhs-logo-300x189.png")

    # with open("style.css") as css:
    #     st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

    #global_page_style('static/css/style.css')

    st.subheader("GIRFT Team Capacity Planner")

    st.markdown(
        """
        ### The tool’s purpose is to allow us to inform the scheduling of new work
        and give us some intelligence on our capacity usage over time and across 
        programmes. It has a calendar that we can use to see scheduled work by the
        day, as well as a dashboard showing capacity over time and by programme 
        and a team leave tracker. 

        What it isn't is a 'bean counting' tool. The tool is not intended to track
        micro levels of activity and shouldn't be overly onerous in terms of admin. 
        For example it doesn't track activity at an individual level and lots of
        categories have been estiamted at a high-level and been added as 
        “indicative” e.g. 1 hour a day per person for general admin time.

        """
        )

    st.write("Head to the other pages below!")

    #st.write(ds.programme_calendar_df)