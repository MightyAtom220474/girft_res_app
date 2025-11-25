import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta
#import matplotlib.pyplot as plt

num_weeks = 52
year = 2025   # you can make this a user input if you want


st.set_page_config(page_title="Weekly Leave Planner", layout="wide")

# load up staff data file
def load_staff_data(staff_base_data):
    # if os.path.exists(staff_base_data):
    df = pd.read_csv(staff_base_data)
    #df["week_commencing"] = pd.to_datetime(df["week_commencing"]).dt.date
    return df
    # else:
    #     df = create_empty(year, staff_list)
    #     df.to_csv(leave_planner_data, index=False)
    #     return df

staff_list = load_staff_data('staff_list.csv')

#print(staff_list)

# get list of staff names
staff_names = staff_list['staff_member'].to_list()
#print(staff_names)

# function to load or create leave planner
def load_or_update_leave_file(filepath, staff_list,leave_type):
    """
    Loads an existing weekly leave CSV OR creates/updates one
    with all weeks of the current year for all staff.

    Weeks are auto-generated based on today's date.
    """

    # -----------------------------------------
    # Auto-generate weekly start/end dates
    # -----------------------------------------
    today = date.today()
    year = today.year

    # First Monday of the year
    first_day = date(year, 1, 1)
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)

    # Last Monday of the year
    last_day = date(year, 12, 31)
    last_monday = last_day - timedelta(days=last_day.weekday())

    # Weekly list of Mondays
    weeks = pd.date_range(start=first_monday, end=last_monday, freq="W-MON")

    # Create full weekly structure
    def create_full_structure(staff):
        rows = []
        for s in staff:
            for w in weeks:
                rows.append({
                    "staff_member": s,
                    "week_commencing": w,
                    "week_number": w.isocalendar().week,
                    leave_type: 0
                })
        return pd.DataFrame(rows)

    # -----------------------------------------
    # CASE 1: File exists → load + update
    # -----------------------------------------
    if os.path.exists(filepath):
        existing = pd.read_csv(filepath, parse_dates=["week_commencing"])

        existing_staff = set(existing["staff_member"].unique())
        new_staff = set(staff_list) - existing_staff

        if new_staff:
            add_df = create_full_structure(new_staff)
            updated = pd.concat([existing, add_df], ignore_index=True)
            updated.to_csv(filepath, index=False)
            return updated

        return existing

    # -----------------------------------------
    # CASE 2: File does not exist → create new file
    # -----------------------------------------
    df = create_full_structure(staff_list)
    df.to_csv(filepath, index=False)
    return df


# def save_data(df):
#     df.to_csv(leave_planner_data, index=False)


# ------------------------------------------------
# Staff list (editable if you want)
# ------------------------------------------------
# staff_list = ["Alice", "Bob", "Charlie"]   # <- replace with your team
staff_names.sort()

# st.subheader("Team Members")
# st.write(", ".join(staff_list))


#leave_calendar_df = load_or_update_leave_file('annual_leave_calendar.csv',staff_names)
#print(leave_calendar_df)


# # set up separate tabs for leave and programme
# tab1, tab2 = st.tabs(["Annual Leave","Programme of Work"])


# with tab1:

#     st.title("📅 Weekly Leave Planner")
#     # ------------------------------------------------
#     # Select staff to edit
#     # ------------------------------------------------
#     st.subheader("✏️ Edit Leave for a Specific Team Member")

#     selected_staff = st.selectbox("Select staff member", staff_list)

#     staff_df = df[df["staff"] == selected_staff].copy().reset_index(drop=True)

#     # ------------------------------------------------
#     # Editable table for selected staff
#     # ------------------------------------------------
#     st.write(f"### Editing: {selected_staff}")

#     edited_df = st.data_editor(
#         staff_df,
#         hide_index=True,
#         num_rows="fixed",
#         column_config={
#             "week": st.column_config.NumberColumn("Week", disabled=True),
#             "week_commencing": st.column_config.DateColumn(
#                 "Week Commencing (Mon)", disabled=True
#             ),
#             "leave_days": st.column_config.NumberColumn(
#                 "Days of Leave",
#                 help="Enter days or fractions (e.g. 0.5)",
#                 step=0.5
#             ),
#             "staff": st.column_config.TextColumn("Staff", disabled=True)
#         }
#     )


#     # ------------------------------------------------
#     # Save updated data
#     # ------------------------------------------------
#     if st.button("💾 Save Changes"):
#         df.loc[df["staff"] == selected_staff, "leave_days"] = edited_df["leave_days"]
#         save_data(df)
#         st.success("All Changes Saved")


#     # ------------------------------------------------
#     # Weekly calendar
#     # ------------------------------------------------
#     st.subheader("📊 Team Calendar View (Weekly Heatmap)")

#     pivot = df.pivot_table(
#         index="staff",
#         columns="week",
#         values="leave_days",
#         fill_value=0
#     )

#     # Manual gradient colouring without matplotlib
#     def cell_color(val):
#         # Scale 0–5 days (feel free to adjust)
#         max_days = 5
#         intensity = min(val / max_days, 1)
#         r = int(255 * intensity)
#         g = int(200 * (1 - intensity))
#         b = 0
#         return f"background-color: rgb({r}, {g}, {b})"

#     # Manual gradient colouring without matplotlib
#     def cell_color(val):
#         # Scale 0–5 days (feel free to adjust)
#         max_days = 5
#         intensity = min(val / max_days, 1)
#         r = int(255 * intensity)
#         g = int(200 * (1 - intensity))
#         b = 0
#         return f"background-color: rgb({r}, {g}, {b})"

#     styled = pivot.style.applymap(cell_color)
#     st.dataframe(styled, use_container_width=True)

#     # ------------------------------------------------
#     # Summary
#     # ------------------------------------------------
#     st.subheader("Summary Stats")

#     summary = df.groupby("staff")["leave_days"].sum().reset_index()
#     summary.columns = ["Staff", "Total Leave (days)"]

#     st.dataframe(summary, hide_index=True)

# with tab2:
    
#     st.title("📅 Programme of Work")
#     st.subheader("✏️ Enter Progamme of Work")

