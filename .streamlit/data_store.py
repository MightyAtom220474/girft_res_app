import os
import pandas as pd
from datetime import date
import planner_functions as pf  # Your existing helper functions

# --------------------------
# Global dataframes
# --------------------------
staff_list = None
programme_list = None
programme_categories = None
programme_calendar_df = None
leave_calendar_df = None
onsite_calendar_df = None
staff_leave_merged_df = None
staff_prog_merged_df = None
staff_prog_combined_df = None
staff_prog_pivot_df = None
staff_leave_df = None
programme_names = None

target_util_rate = 85


def load_or_refresh_all():
    """
    Loads all dataframes (if missing) AND performs all downstream merges
    and calculated fields—so every page sees consistent updated values.
    """
    global staff_list, programme_list, programme_names
    global leave_calendar_df, onsite_calendar_df, programme_calendar_df
    global staff_leave_merged_df, staff_prog_merged_df
    global staff_prog_combined_df, staff_leave_df

    import planner_functions as pf
    import pandas as pd

    # ---------------------------
    # 1️⃣ Load raw base data
    # ---------------------------
    if staff_list is None:
        staff_list = pf.load_data("staff_list.csv")

    if programme_list is None:
        programme_list = pf.load_data("programme_categories.csv")

    staff_names = staff_list['staff_member'].tolist()
    staff_names.sort()

    # Convert programme_list to dicts for planner (archive check)
    programme_categories = programme_list.to_dict(orient="records")

    # ---------------------------
    # 2️⃣ Load or update programme calendar
    # ---------------------------
    programme_calendar_df = pf.load_or_update_planner_file(
        "programme_calendar.csv",
        staff_names,
        programme_categories
    )

    # ---------------------------
    # 3️⃣ Only keep non-archived programme names that exist as columns
    # ---------------------------
    active_programmes = [
        p["programme_categories"] for p in programme_categories if p["archive_flag"] == 0
    ]

    # Safe intersection with actual DataFrame columns
    programme_names = [p for p in active_programmes if p in programme_calendar_df.columns]

    # ---------------------------
    # 4️⃣ Compute total activity hours safely
    # ---------------------------
    if programme_names:  # only sum if there are columns to sum
        programme_calendar_df['total_prog_hours'] = programme_calendar_df[programme_names].sum(axis=1)
    else:
        programme_calendar_df['total_prog_hours'] = 0

    # ---------------------------
    # 5️⃣ Load other calendars safely
    # ---------------------------
    if leave_calendar_df is None:
        leave_calendar_df = pf.load_or_update_leave_file(
            "annual_leave_calendar.csv", staff_names, "days_leave"
        )

    if onsite_calendar_df is None:
        onsite_calendar_df = pf.load_or_update_leave_file(
            "on_site_calendar.csv", staff_names, "on_site_days"
        )

    # ---------------------------
    # 6️⃣ Merge / calculated fields as before
    # ---------------------------
    # Convert leave days to hours
    leave_calendar_df['leave_hours'] = leave_calendar_df['days_leave'] * 7.5

    

    # Merge leave with staff list so can access working hours etc.
    staff_leave_merged_df = leave_calendar_df.merge(
        staff_list, on="staff_member", how="left"
    )
    
    staff_leave_merged_df['avail_hours'] = staff_leave_merged_df['hours_pw'] - staff_leave_merged_df['leave_hours']

    ##### Programme Summary #####
    # Merge programme calendar with staff
    staff_prog_merged_df = programme_calendar_df.merge(
        staff_list, on="staff_member", how="left"
    )
  
    # pivot leave to get total by week
    staff_leave_df = leave_calendar_df.groupby(['staff_member','week_number']).agg(
                    total_leave_hours =('leave_hours','sum')).reset_index()

    staff_prog_combined_df = staff_prog_merged_df.merge(
        staff_leave_df, on=["staff_member","week_number"], how="left")
    
    
    # add available hours
    staff_prog_combined_df['total_contr_hours'] = staff_prog_combined_df['hours_pw']
    # add available hours
    staff_prog_combined_df['total_avail_hours'] = staff_prog_combined_df['hours_pw'] - staff_prog_combined_df['total_leave_hours']
    # add non-deployable hours
    staff_prog_combined_df['total_non_deploy_hours'] = staff_prog_combined_df['total_avail_hours'] * (1 - staff_prog_combined_df['deploy_ratio'])
    # total utilised hours = deployable plus non-deployable
    staff_prog_combined_df["total_util_hours"] = staff_prog_combined_df["total_prog_hours"] + staff_prog_combined_df["total_non_deploy_hours"]
    # pivot to summarise all required columns by week
    staff_prog_pivot_df = staff_prog_combined_df.groupby("week_number").agg({
    "total_leave_hours": "sum", # leave booked
    "total_contr_hours": "sum", # contracted hours
    "total_avail_hours": "sum", # contracted hours minus leave
    "total_prog_hours": "sum", # deployable hours
    "total_non_deploy_hours": "sum", # non-deployable hours
    "total_util_hours": "sum" # utilised hours
    }).reset_index()

    # calculate utilisation rate
    staff_prog_pivot_df["util_rate"] = (staff_prog_pivot_df["total_util_hours"] / staff_prog_pivot_df["total_avail_hours"]) * 100
    staff_prog_pivot_df["util_target"] = 85

    # ---------------------------
    # 7️⃣ Assign back to globals
    # ---------------------------
    globals().update({
        "programme_calendar_df": programme_calendar_df,
        "programme_names": programme_names,
        "leave_calendar_df": leave_calendar_df,
        "onsite_calendar_df": onsite_calendar_df,
        "staff_leave_merged_df": staff_leave_merged_df,
        "staff_prog_merged_df": staff_prog_merged_df,
        "staff_prog_combined_df": staff_prog_combined_df,
        "staff_leave_df": staff_leave_df,
        "staff_prog_pivot_df": staff_prog_pivot_df
    })