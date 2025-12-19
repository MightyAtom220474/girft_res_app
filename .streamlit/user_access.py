import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash
import data_store as ds

# Load data
ds.load_or_refresh_all()

# Ensure column exists
if "must_change_password" not in ds.staff_list.columns:
    ds.staff_list["must_change_password"] = True
    ds.staff_list.to_csv("staff_list.csv", index=False)

def login_page():
    st.title("Login")

    # ---------------------------
    # NOT LOGGED IN
    # ---------------------------
    if not st.session_state.get("logged_in", False):

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            user_row = ds.staff_list[ds.staff_list["username"] == username]

            if user_row.empty:
                st.error("Invalid username or password")
                return

            stored_hash = user_row.iloc[0]["password"]

            if not check_password_hash(stored_hash, password):
                st.error("Invalid username or password")
                return

            # Login success
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.access_level = user_row.iloc[0]["access_level"]
            st.session_state.must_change_password = user_row.iloc[0]["must_change_password"]

            st.rerun()

    # ---------------------------
    # FORCE PASSWORD CHANGE
    # ---------------------------
    if st.session_state.get("logged_in") and st.session_state.get("must_change_password"):

        st.warning("You must change your password before continuing.")

        new_password = st.text_input("New password", type="password", key="pw_new")
        confirm_password = st.text_input("Confirm password", type="password", key="pw_confirm")

        if st.button("Update password", key="pw_update"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return

            if len(new_password) < 8:
                st.error("Password must be at least 8 characters")
                return

            hashed = generate_password_hash(new_password)

            ds.staff_list.loc[
                ds.staff_list["username"] == st.session_state.username, "password"
            ] = hashed

            ds.staff_list.loc[
                ds.staff_list["username"] == st.session_state.username,
                "must_change_password"
            ] = False

            ds.staff_list.to_csv("staff_list.csv", index=False)

            st.session_state.must_change_password = False
            st.success("Password updated successfully")

            st.rerun()

    # ---------------------------
    # LOGGED IN & READY
    # ---------------------------
    if st.session_state.get("logged_in") and not st.session_state.get("must_change_password"):
        st.success(f"Logged in as {st.session_state.username}")



