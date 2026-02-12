import streamlit as st
from user_access import login_page
from homepage import homepage
from planner_app import planner
from record_leave import leave
from record_block import block
from dashboard import dashboard
from maintenance import maintenance

def secure_page(page_func, allowed_levels):
    def wrapped():
        if not st.session_state.get("logged_in", False):
            st.warning("Please log in to access this page.")
        elif st.session_state.access_level not in allowed_levels:
            st.error("You do not have permission to access this page.")
        else:
            page_func()

    wrapped.__name__ = f"secure_{page_func.__name__}"
    return wrapped


def render_navigation():
    
    with st.sidebar:
        st.title("📋 Navigation")

        pages = {
            "Login": "🔑 Login",
            "Homepage": "🏠 Homepage",
            "Activity": "🧩 Weekly Activity",
            "Leave": "✈️ Leave Record",
            "Planner" : "🗓️ Forward Planner",
            "Dashboard": "📊 Capacity Dashboard",
            "Maintenance": "🛠️ System Maintenance",
        }

        if "active_page" not in st.session_state:
            st.session_state.active_page = "Login"

        selected = st.radio(
            "Go to",
            list(pages.keys()),
            format_func=lambda x: pages[x],
            index=list(pages.keys()).index(st.session_state.active_page),
        )

        st.session_state.active_page = selected

        # -------------------------
        # Push logout to bottom
        # -------------------------
        st.markdown("<br>" * 8, unsafe_allow_html=True)

        if st.session_state.get("logged_in"):
            st.divider()

            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = None
                st.session_state.access_level = None
                st.session_state.must_change_password = False
                st.session_state.active_page = "Login"
                st.rerun()

    # -------------------------
    # Router
    # -------------------------
    page = st.session_state.active_page

    if page == "Login":
        login_page()

    elif page == "Homepage":
        secure_page(homepage, ["admin", "user", "viewer"])()

    elif page == "Planner":
        secure_page(block, ["admin", "user"])()

    elif page == "Activity":
        secure_page(planner, ["admin", "user"])()

    elif page == "Leave":
        secure_page(leave, ["admin", "user"])()

    elif page == "Dashboard":
        secure_page(dashboard, ["admin", "viewer"])()

    elif page == "Maintenance":
        secure_page(maintenance, ["admin"])()




