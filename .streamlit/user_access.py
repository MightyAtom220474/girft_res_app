import streamlit as st
import sqlite3
import time
import pandas as pd
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "girft_capacity_planner.db"  # make sure this is the ONE DB used everywhere

login_prompt = ("Username is your .net email account, all lowercase!\n"
                " On first login you will be prompted to set your own password")

def stream_data():
    for ch in login_prompt:
        yield ch
        time.sleep(0.02)
        
def login_page():

    st.image("https://gettingitrightfirsttime.co.uk/wp-content/uploads/2022/06/cropped-GIRFT-Logo-300-RGB-Large.jpg", width=300)

    st.title("Login")

    # if not st.session_state.get("logged_in", False):
    #     st.write_stream(stream_data())

    # ---------------------------
    # NOT LOGGED IN
    # ---------------------------
    if not st.session_state.get("logged_in", False):

        st.write(login_prompt)
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT password, access_level, must_change_password
                    FROM staff_list
                    WHERE username = ?
                """, (username,))
                row = cur.fetchone()

            if not row:
                st.error("Invalid username or password")
                return

            stored_hash, access_level, must_change = row

            if not check_password_hash(stored_hash, password):
                st.error("Invalid username or password")
                return

            st.session_state.logged_in = True
            st.session_state.username = username
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

            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE staff_list
                    SET password = ?,
                        must_change_password = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE username = ?
                """, (hashed, st.session_state.username))
                conn.commit()

                if cur.rowcount != 1:
                    st.error("Password update failed (user not found).")
                    return

            st.session_state.must_change_password = False
            st.success("Password updated successfully")
            st.rerun()

    # ---------------------------
    # LOGGED IN & READY
    # ---------------------------
    if st.session_state.get("logged_in") and not st.session_state.get("must_change_password"):
        st.success(f"Logged in as {st.session_state.username}")