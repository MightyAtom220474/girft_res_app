import streamlit as st
from navigation import render_navigation

# Session defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_level = None

render_navigation()



