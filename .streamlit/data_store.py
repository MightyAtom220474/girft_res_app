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
staff_leave_df = None
programme_names = None


def load_or_refresh_all():
    """
    Load all dataframes if missing and perform downstream merges
    and calculated fields — ensures every page sees consistent updated values.
    """

    global staff_list, programme_list, programme_categories, programme_calendar_df
    global leave_calendar_df, onsite_calendar_df
    global staff_leave_merged_df, staff_prog_merged_df
    global staff_prog_combined_df, staff_leave_df, programme_names

    # ---------------------------
    # 1️⃣ Load base data
    # ---------------------------
    if staff_list is None:
        staff_list = pf.load_data("staff_list.csv")

    if programme_list is None:
        programme_list = pf.load_data("programme_categories.csv")

    # Convert programme list to dicts for planner (archive_flag, group, etc.)
    programme_categories = programme_list.to_dict(orient="records")

    # Active staff only
    staff_names = staff_list.loc[staff_list["archive_flag"] == 0, "staff_member"].sort_values().tolist()

    # ---------------------------
    # 2️⃣ Load / update programme calendar
    # ---------------------------
    programme_calendar_path = "programme_calendar.csv"
    programme_calendar_df = pf.load_or_update_planner_file(
        programme_calendar_path,
        staff_names,
        programme_categories
    )

    # Compute active programme columns (exclude base columns)
    base_cols = {"staff_member", "week_commencing", "week_number"}
    programme_names = [c for c in programme_calendar_df.columns if c not in base_cols]

    # Total activity hours
    programme_calendar_df["total_act_hours"] = programme_calendar_df[programme_names].sum(axis=1)

    # ---------------------------
    # 3️⃣ Load / update leave calendar
    # ---------------------------
    leave_calendar_path = "annual_leave_calendar.csv"
    leave_calendar_df = pf.load_or_update_leave_file(
        leave_calendar_path,
        staff_names,
        "days_leave"
    )

    # Convert leave days to hours
    leave_calendar_df["leave_hours"] = leave_calendar_df["days_leave"] * 7.5

    # ---------------------------
    # 4️⃣ Load / update on-site calendar
    # ---------------------------
    onsite_calendar_path = "on_site_calendar.csv"
    onsite_calendar_df = pf.load_or_update_leave_file(
        onsite_calendar_path,
        staff_names,
        "on_site_days"
    )

    # ---------------------------
    # 5️⃣ Merge leave with staff
    # ---------------------------
    staff_leave_merged_df = leave_calendar_df.merge(
        staff_list,
        on="staff_member",
        how="left"
    )

    staff_leave_merged_df["avail_hours"] = staff_leave_merged_df["hours_pw"] - staff_leave_merged_df["leave_hours"]

    # ---------------------------
    # 6️⃣ Merge programme calendar with staff
    # ---------------------------
    staff_prog_merged_df = programme_calendar_df.merge(
        staff_list,
        on="staff_member",
        how="left"
    )

    # ---------------------------
    # 7️⃣ Combine programme + leave for available hours
    # ---------------------------
    staff_leave_df = leave_calendar_df[["staff_member", "week_number", "leave_hours"]]

    staff_prog_combined_df = staff_prog_merged_df.merge(
        staff_leave_df,
        on=["staff_member", "week_number"],
        how="left"
    )

    staff_prog_combined_df["avail_hours"] = staff_prog_combined_df["hours_pw"] - staff_prog_combined_df["leave_hours"]

    # Non-deployable hours = avail_hours * (1 - deploy_ratio)
    staff_prog_combined_df["non-deployable_hours"] = staff_prog_combined_df["avail_hours"] * \
                                                      (1 - staff_prog_combined_df["deploy_ratio"])

