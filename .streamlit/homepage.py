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
        #st.write("Email: info@gettingitrightfirsttime.co.uk")

    st.divider()
    
    # with open("style.css") as css:
    #     st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

    #global_page_style('static/css/style.css')



    st.subheader("Welcome to the **GIRFT Team Capacity Planner**.")

    st.markdown(
    """
     This tool replaces the previous Excel based capacity planner for recording
     leave and programme activity. The tool helps the team to schedule new work
     and supports workforce planning by providing visibility of capacity and
     activity across programmes and the wider team.
    """
    )

    st.divider()

    st.subheader("What this tool helps you do")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success("🧩**Weekly Activity**\n\nThis is where you can record your hours worked per week per programme.\n\n")

    with col2:
        st.info("✈️ **Leave Record**\n\nThis where you can record leave.\n\n\n\n")

    with col3:
        st.warning("📅 **Forward Planner**\n\nThis is where you can block out whole days for any on-site or other full-day commitment activities when you are unavailable e.g. Men-SAT, Further Faster, study etc.")

    with col4:
        st.error("📊**Capacity Dashboard**\n\nThis is where you can find the team capacity dashboard showing team demand and capacity, programme activity and team availability heatmaps.")
    
    st.divider()

    # --- What the tool is not ---
    st.subheader("What this tool is not")

    st.markdown(
    """
    This is **NOT** intended as a ‘bean counting’ tool. It is **NOT** designed to track
     micro-levels of activity (e.g. x person attended y meeting on Wednesday)
     and has been designed to minimise the administrative burden associated 
     with inputting activity. The tool is designed to support planning
     conversations — **NOT** for performance monitoring purposes.
    """
    )
