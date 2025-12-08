import streamlit as st
import data_store as ds
import planner_functions as pf

def homepage():

    ds.load_or_refresh_all()

    st.logo("https://lancsvp.org.uk/wp-content/uploads/2021/08/nhs-logo-300x189.png")

    # with open("style.css") as css:
    #     st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

    #global_page_style('static/css/style.css')

    st.subheader("GIRFT Team Capacity Planner")

    st.markdown(
        """
        ## The tool’s purpose is to allow us to inform the scheduling of new work 
        # and give us some intelligence on our capacity usage over time and across 
        programmes. It has a calendar that we can use to see scheduled work by the
        week, as well as a dashboard showing capacity over time and by programme 
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