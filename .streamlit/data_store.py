import pandas as pd
import planner_functions as pf

# Global dataframes
staff_list = None
programme_list = None
programme_names = None
leave_calendar_df = None
onsite_calendar_df = None
programme_calendar_df = None
staff_leave_merged_df = None
staff_prog_merged_df = None
staff_prog_combined_df = None
staff_leave_df = None


def load_or_refresh_all():
    """
    Loads all dataframes (if missing) AND performs all downstream merges
    and calculated fields—so every page sees consistent updated values.
    """
    global staff_list, programme_list, programme_names
    global leave_calendar_df, onsite_calendar_df, programme_calendar_df
    global staff_leave_merged_df, staff_prog_merged_df
    global staff_prog_combined_df, staff_leave_df

    # ---------------------------
    # Load raw base data
    # ---------------------------
    if staff_list is None:
        staff_list = pf.load_data("staff_list.csv")

    if programme_list is None:
        programme_list = pf.load_data("programme_categories.csv")

    staff_names = staff_list['staff_member'].tolist()
    staff_names.sort()

    programme_names = programme_list['programme_categories'].tolist()
    programme_names.sort()

    if leave_calendar_df is None:
        leave_calendar_df = pf.load_or_update_leave_file(
            "annual_leave_calendar.csv",
            staff_names,
            "days_leave"
        )

    if onsite_calendar_df is None:
        onsite_calendar_df = pf.load_or_update_leave_file(
            "on_site_calendar.csv",
            staff_names,
            "on_site_days"
        )

    if programme_calendar_df is None:
        programme_calendar_df = pf.load_or_update_planner_file(
            "programme_calendar.csv",
            staff_names,
            programme_names
        )

    # ---------------------------
    # Derived & merged fields
    # ---------------------------

    # Leave hours
    leave_calendar_df["leave_hours"] = leave_calendar_df["days_leave"] * 7.5

    # Programme totals
    programme_calendar_df["total_act_hours"] = programme_calendar_df[programme_names].sum(axis=1)

    # Merge with staff list
    staff_leave_merged_df = leave_calendar_df.merge(staff_list, on="staff_member", how="left")

    # Available hours
    staff_leave_merged_df["avail_hours"] = (
        staff_leave_merged_df["hours_pw"] - staff_leave_merged_df["leave_hours"]
    )

    # Programme merged
    staff_prog_merged_df = programme_calendar_df.merge(staff_list, on="staff_member", how="left")

    # Simplified leave subset
    staff_leave_df = leave_calendar_df[["staff_member", "week_number", "leave_hours"]]

    # Combined programme + leave
    staff_prog_combined_df = staff_prog_merged_df.merge(
        staff_leave_df, on=["staff_member", "week_number"], how="left"
    )

    staff_prog_combined_df["avail_hours"] = (
        staff_prog_combined_df["hours_pw"] - staff_prog_combined_df["leave_hours"]
    )

    staff_prog_combined_df["non-deployable hours"] = (
        staff_prog_combined_df["avail_hours"] * (1 - staff_prog_combined_df["deploy_ratio"])
    )
