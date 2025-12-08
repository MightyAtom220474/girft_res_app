import streamlit as st
from planner_app import planner as planner_page
from homepage import homepage as home_page
from dashboard import dashboard as dashboard_page
from maintenance import maintenance as maintenance_page

pg = st.navigation(
    [
        st.Page(home_page, title="Homepage", icon=":material/add_circle:"),
        st.Page(planner_page, title="Capacity Planner", icon=":material/public:"),
        st.Page(dashboard_page, title="Capacity Dashboard", icon=":material/public:"),
        st.Page(maintenance_page, title="System Maintenance", icon=":material/public:")
    ]
)

pg.run()

