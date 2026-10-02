import pandas as pd
import numpy as np
#from datetime import date
#from dateutil.relativedelta import relativedelta
#import sqlite3
import streamlit as st
#import os
import planner_functions as pf

#from foundry.transforms import Dataset
import pandas as pd
# import streamlit as st
#from config import DB_PATH

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "girft_capacity_planner.db")

target_util_rate = 85
default_password = 'Temporary123!'

# staff_list = None
# programme_list = None
# programme_categories = None
# programme_calendar_df = None
# leave_calendar_df = None
# onsite_calendar_df = None
# staff_leave_merged_df = None
# staff_prog_merged_df = None
# staff_prog_combined_df = None
# staff_detail_monthly_df = None
# staff_prog_pivot_df = None
# staff_leave_df = None
# programme_names = None
# staff_names = None

def parse_week_commencing(df, col="week_commencing"):
    if col not in df.columns:
        return df

    s = df[col].replace(["", " ", "None", None], np.nan)
    parsed = pd.to_datetime(s, errors="coerce")

    mask = parsed.isna() & s.notna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(
            s[mask], format="%d/%m/%Y", dayfirst=True, errors="coerce"
        )

    df[col] = parsed.dt.normalize()
    return df

# def load_foundry_dataset(alias):
#     ds = Dataset.get(alias)
#     file = list(ds.files())[0]
#     local_path = file.download()
#     return pd.read_csv(local_path)


# @st.cache_data(ttl=300, show_spinner=False)
# def load_foundry_dataset(alias):
#     """
#     Downloads and loads a Foundry dataset resource.

#     ttl=300 means Streamlit will re-read the dataset every 5 minutes.
#     """
#     ds = Dataset.get(alias)
#     file = list(ds.files())[0]
#     local_path = file.download()
#     return pd.read_csv(local_path)


def load_or_refresh_all():

    # ✅ Initialise ALL expected session state keys first
    defaults = {
        "staff_list": pd.DataFrame(),
        "programme_list": pd.DataFrame(),
        "programme_calendar_df": pd.DataFrame(),
        "leave_calendar_df": pd.DataFrame(),
        "onsite_calendar_df": pd.DataFrame(),
        "staff_week_capacity_df": pd.DataFrame(),
        "staff_prog_pivot_df": pd.DataFrame(),
        "staff_prog_monthly_df": pd.DataFrame(),
        "staff_detail_monthly_df": pd.DataFrame(),
        "programme_names": [],
        "staff_names": []
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # ------------------------------------------------------------------
    # Load Foundry datasets
    # ------------------------------------------------------------------

    staff_list = pf.load_foundry_dataset("staff_list_0")

    if "archive_flag" in staff_list.columns:
        staff_list = staff_list[
            pd.to_numeric(
                staff_list["archive_flag"],
                errors="coerce"
            ).fillna(0).astype(int) == 0
        ]

    programme_list = pf.load_foundry_dataset("programme_categories_0")

    if "archive_flag" in programme_list.columns:
        programme_list = programme_list[
            pd.to_numeric(
                programme_list["archive_flag"],
                errors="coerce"
            ).fillna(0).astype(int) == 0
        ]

    programme_calendar_df = pf.load_foundry_dataset("programme_activity_0")

    leave_calendar_raw = pf.load_foundry_dataset("leave_calendar_0")

    leave_calendar_df = (
        leave_calendar_raw
        .groupby(
            ["staff_member", "week_commencing", "week_number"],
            as_index=False
        )["days_leave"]
        .sum()
    )

    onsite_calendar_raw = pf.load_foundry_dataset("on_site_calendar_0")

    onsite_calendar_df = (
        onsite_calendar_raw
        .groupby(
            ["staff_member", "week_commencing", "week_number"],
            as_index=False
        )["on_site_days"]
        .sum()
    )

    # ------------------------------------------------------------------
    # Store in session state
    # ------------------------------------------------------------------

    st.session_state.staff_list = staff_list
    st.session_state.programme_list = programme_list
    st.session_state.programme_calendar_df = programme_calendar_df
    st.session_state.leave_calendar_df = leave_calendar_df
    st.session_state.onsite_calendar_df = onsite_calendar_df

    if (
        not programme_list.empty
        and "programme" in programme_list.columns
    ):
        st.session_state.programme_names = sorted(
            programme_list["programme"]
            .dropna()
            .unique()
            .tolist()
        )

    if (
        not staff_list.empty
        and "staff_member" in staff_list.columns
    ):
        st.session_state.staff_names = sorted(
            staff_list["staff_member"]
            .dropna()
            .unique()
            .tolist()
        )


