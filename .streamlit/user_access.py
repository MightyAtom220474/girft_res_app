import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash
from data_store import staff_list  # your existing dataframe
import data_store as ds

ds.load_or_refresh_all()

# Convert staff_list dataframe to a dict for authentication
users = {}
for _, row in ds.staff_list.iterrows():
    users[row['username']] = {
        "password": generate_password_hash(row['password']),
        "access_level": row['access_level']
    }

def check_login(username, password):
    if username in users and check_password_hash(users[username]["password"], password):
        return True, users[username]["access_level"]
    return False, None

def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        success, access_level = check_login(username, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.access_level = access_level
            st.success(f"Logged in as {username} ({access_level})")
        else:
            st.error("Invalid username or password")
