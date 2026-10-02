import streamlit as st
# import sqlite3
# import time
import pandas as pd
# import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from planner_functions import load_foundry_dataset, save_foundry_dataset


login_prompt = ("Username is your .net email account, all lowercase!\n"
                " On first login you will be prompted to set your own password")

@st.cache_data(ttl=300, show_spinner=False)

def login_page():

    st.set_page_config(layout="wide")

    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        st.header("🔑 User Login")
    with col2:
        st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)
        #st.write("Email: info@gettingitrightfirsttime.co.uk")

    # ---------------------------
    # NOT LOGGED IN
    # ---------------------------
    if not st.session_state.get("logged_in", False):

        st.write(login_prompt)
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):

            staff_df = load_foundry_dataset("staff_list_0")

            user_row = staff_df[
                staff_df["username"].astype(str).str.strip()
                == username.strip()
            ]

            if user_row.empty:
                st.error("Invalid username or password")
                return

            user = user_row.iloc[0]

            stored_hash = user["password"]
            access_level = user["access_level"]
            must_change = user["must_change_password"]
            staff_member = user["staff_member"]

            if not check_password_hash(stored_hash, password):
                st.error("Invalid username or password")
                return

            # ---------------------------
            # STORE SESSION STATE
            # ---------------------------
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.staff_member = staff_member   # ✅ NEW LINE
            st.session_state.access_level = access_level
            st.session_state.must_change_password = bool(must_change)

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

            staff_df = load_foundry_dataset("staff_list_0")

            mask = (
                staff_df["username"].astype(str).str.strip()
                == st.session_state.username
            )

            if not mask.any():
                st.error("Password update failed (user not found).")
                return

            staff_df.loc[mask, "password"] = hashed
            staff_df.loc[mask, "must_change_password"] = 0
            staff_df.loc[mask, "updated_at"] = pd.Timestamp.now()

            save_foundry_dataset(
                "staff_list_0",
                staff_df
            )

            st.session_state.must_change_password = False
            st.success("Password updated successfully")
            st.rerun()

    # ---------------------------
    # LOGGED IN & READY
    # ---------------------------
    if st.session_state.get("logged_in") and not st.session_state.get("must_change_password"):
        st.success(f"Logged in as {st.session_state.username}")