import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
#import matplotlib.pyplot as plt

FILE = "weekly_leave_multi.csv"
NUM_WEEKS = 52
YEAR = 2025   # you can make this a user input if you want


st.set_page_config(page_title="Weekly Leave Planner", layout="wide")
st.title("📅 Multi-Staff Weekly Leave Planner")


# ------------------------------------------------
# Helper: get week commencing Monday date
# ------------------------------------------------
def week_commencing(year, week):
    return datetime.strptime(f'{year}-W{int(week)}-1', "%G-W%V-%u").date()


# ------------------------------------------------
# Create empty structure
# ------------------------------------------------
def create_empty(year, staff_list):
    rows = []
    for staff in staff_list:
        for week in range(1, NUM_WEEKS + 1):
            rows.append({
                "staff": staff,
                "week": week,
                "week_commencing": week_commencing(year, week),
                "leave_days": 0.0
            })
    df = pd.DataFrame(rows)
    return df


# ------------------------------------------------
# Load or create CSV
# ------------------------------------------------
def load_data(staff_list):
    if os.path.exists(FILE):
        df = pd.read_csv(FILE)
        df["week_commencing"] = pd.to_datetime(df["week_commencing"]).dt.date
        return df
    else:
        df = create_empty(YEAR, staff_list)
        df.to_csv(FILE, index=False)
        return df


def save_data(df):
    df.to_csv(FILE, index=False)


# ------------------------------------------------
# Staff list (editable if you want)
# ------------------------------------------------
staff_list = ["Alice", "Bob", "Charlie"]   # <- replace with your team
staff_list.sort()

st.subheader("Team Members")
st.write(", ".join(staff_list))


# ------------------------------------------------
# Load existing or create new
# ------------------------------------------------
df = load_data(staff_list)


# ------------------------------------------------
# Select staff to edit
# ------------------------------------------------
st.subheader("✏️ Edit Leave for a Specific Team Member")

selected_staff = st.selectbox("Select staff member", staff_list)

staff_df = df[df["staff"] == selected_staff].copy().reset_index(drop=True)


# ------------------------------------------------
# Editable table for selected staff
# ------------------------------------------------
st.write(f"### Editing: {selected_staff}")

edited_df = st.data_editor(
    staff_df,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "week": st.column_config.NumberColumn("Week", disabled=True),
        "week_commencing": st.column_config.DateColumn(
            "Week Commencing (Mon)", disabled=True
        ),
        "leave_days": st.column_config.NumberColumn(
            "Days of Leave",
            help="Enter days or fractions (e.g. 0.5)",
            step=0.5
        ),
        "staff": st.column_config.TextColumn("Staff", disabled=True)
    }
)


# ------------------------------------------------
# Save updated data
# ------------------------------------------------
if st.button("💾 Save Changes"):
    df.loc[df["staff"] == selected_staff, "leave_days"] = edited_df["leave_days"]
    save_data(df)
    st.success("Saved!")


# ------------------------------------------------
# Weekly heatmap-style calendar
# ------------------------------------------------
st.subheader("📊 Team Calendar View (Weekly Heatmap)")

pivot = df.pivot_table(
    index="staff",
    columns="week",
    values="leave_days",
    fill_value=0
)

# Manual gradient colouring without matplotlib
def cell_color(val):
    # Scale 0–5 days (feel free to adjust)
    max_days = 5
    intensity = min(val / max_days, 1)
    r = int(255 * intensity)
    g = int(200 * (1 - intensity))
    b = 0
    return f"background-color: rgb({r}, {g}, {b})"

# Manual gradient colouring without matplotlib
def cell_color(val):
    # Scale 0–5 days (feel free to adjust)
    max_days = 5
    intensity = min(val / max_days, 1)
    r = int(255 * intensity)
    g = int(200 * (1 - intensity))
    b = 0
    return f"background-color: rgb({r}, {g}, {b})"

styled = pivot.style.applymap(cell_color)
st.dataframe(styled, use_container_width=True)



# ------------------------------------------------
# Summary
# ------------------------------------------------
st.subheader("Summary Stats")

summary = df.groupby("staff")["leave_days"].sum().reset_index()
summary.columns = ["Staff", "Total Leave (days)"]

st.dataframe(summary, hide_index=True)

