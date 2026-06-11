import os
import pandas as pd
import psycopg2
import streamlit as st
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse


from dotenv import load_dotenv
load_dotenv()

# ============================================================
# CONNECTION (cached for Streamlit performance)
# ============================================================
def get_db_url():
    return os.getenv("DATABASE_URL_PUBLIC")

# -----------------------------
# CONNECTION
# -----------------------------

@st.cache_resource
def get_conn():
    db_url = os.getenv("DATABASE_URL_PUBLIC")

    if not db_url:
        raise ValueError("DATABASE_URL_PUBLIC not found")

    url = urlparse(db_url)

    return psycopg2.connect(
        dbname=url.path[1:],   # removes leading '/'
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode="require",
        options="-c gssencmode=disable"
    )


# @st.cache_resource
# def get_conn():
#     db_url = get_db_url()

#     if not db_url:
#         raise ValueError(
#             "DATABASE_URL not found. Check Railway or .env variables."
#         )

#     return psycopg2.connect(db_url, sslmode="require")

# ============================================================
# EXECUTE (INSERT / UPDATE / DELETE)
# ============================================================
def execute(query, params=None):
    """
    Run a query that does NOT return a dataframe.
    """

    conn = get_conn()

    with conn.cursor() as cur:
        cur.execute(query, params or [])
        conn.commit()


# ============================================================
# QUERY → DATAFRAME (SELECT)
# ============================================================
def query_df(query, params=None):
    """
    Run SELECT queries and return a pandas DataFrame.
    """

    conn = get_conn()

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params or [])
        rows = cur.fetchall()

        return pd.DataFrame(rows)


# ============================================================
# OPTIONAL: SIMPLE QUERY (if you ever need raw rows)
# ============================================================
def query_rows(query, params=None):
    """
    Returns raw rows (list of tuples).
    Rarely needed, but included for flexibility.
    """

    conn = get_conn()

    with conn.cursor() as cur:
        cur.execute(query, params or [])
        return cur.fetchall()
    

# import psycopg2

# conn = psycopg2.connect(
#     dbname="railway",
#     user="postgres",
#     password="Temporary123",
#     host="zephyr.proxy.rlwy.net",
#     port=17430,
#     sslmode="require"
#     )

# print("✅ Connected!")
