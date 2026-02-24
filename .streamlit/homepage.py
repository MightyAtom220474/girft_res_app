import streamlit as st
import data_store as ds
import planner_functions as pf

def homepage():

    ds.load_or_refresh_all()

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("🏠 Capacity Planner Homepage")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        st.write("Email: info@gettingitrightfirsttime.co.uk")

    st.divider()
    
    # with open("style.css") as css:
    #     st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

    #global_page_style('static/css/style.css')


    # Page title
    

    st.markdown(
    """
    Welcome to the **GIRFT Team Capacity Planner**.

    This tool helps teams plan work effectively by providing visibility of capacity,
    scheduled activity, and availability across programmes.
    """
    )

    st.divider()

    # --- What the tool does ---
    st.subheader("What this tool helps you do")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("📅 **View scheduled work**\n\nSee planned activity by week using the calendar.")

    with col2:
        st.info("📊 **Monitor capacity**\n\nTrack capacity over time and across programmes.")

    with col3:
        st.info("🏖️ **Track team leave**\n\nUnderstand availability with the leave tracker.")

    st.divider()

    # --- What the tool is not ---
    st.subheader("What this tool is not")

    st.markdown(
    """
    This is **not** a ‘bean counting’ tool.

    It is not designed to track micro-levels of activity and should not create unnecessary
    administrative burden.

    - Activity is **not tracked at an individual level**
    - Many categories are **high-level estimates**
    - Some values are **indicative**, such as allocating time for general admin
    (e.g. 1 hour per person per day)
    """
    )

    st.divider()

    st.caption("Designed to support planning conversations — not detailed performance tracking.")



    #st.write(ds.programme_calendar_df)