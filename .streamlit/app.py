import streamlit as st
from user_access import login_page
from homepage import homepage as home_page
from planner_app import planner as planner_page
from dashboard import dashboard as dashboard_page
from maintenance import maintenance as maintenance_page

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_level = None

# Wrapper for access control
def secure_page(page_func, allowed_levels):
    def wrapped():
        if not st.session_state.logged_in:
            st.warning("Please log in to access this page.")
        elif st.session_state.access_level not in allowed_levels:
            st.error("You do not have permission to access this page.")
        else:
            page_func()

    # Give a unique name based on the original page function
    wrapped.__name__ = f"secure_{page_func.__name__}"
    return wrapped

# Navigation setup
pg = st.navigation(
    [
        st.Page(login_page, title="Login", icon="🔑"),
        st.Page(secure_page(home_page, ["admin", "user", "viewer"]),title="Homepage", icon="🏠"),
        st.Page(secure_page(planner_page, ["admin", "user"]), title="Capacity Planner", icon="🗓️"),
        st.Page(secure_page(dashboard_page, ["admin", "user", "viewer"]), title="Capacity Dashboard", icon="📊"),
        st.Page(secure_page(maintenance_page, ["admin"]), title="System Maintenance", icon="🛠️")
    ]
)

pg.run()
