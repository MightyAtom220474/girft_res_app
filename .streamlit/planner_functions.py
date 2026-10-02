import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import re
#import os
from datetime import date, timedelta
# import data_store as ds
from werkzeug.security import generate_password_hash
#import matplotlib.pyplot as plt
import plotly.graph_objects as go
#import numpy as np
from foundry.transforms import Dataset

from config import DB_PATH
import data_store as ds

num_weeks = 52
year = 2025   # you can make this a user input if you want
decimals = 1 # number of decimal places


def make_activity_chart(activity_calendar_df, programme_names):
    import plotly.graph_objects as go

    # Pivot normalised data → wide just for plotting
    plot_df = (
        activity_calendar_df
        .groupby(["week_number", "programme_category"], as_index=False)
        .agg(activity_value=("activity_value", "sum"))
        .pivot(
            index="week_number",
            columns="programme_category",
            values="activity_value"
        )
        .fillna(0)
        .sort_index()
    )

    fig = go.Figure()

    for programme in programme_names:
        if programme in plot_df.columns:
            fig.add_trace(
                go.Bar(
                    x=plot_df.index,
                    y=plot_df[programme],
                    name=programme
                )
            )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Week",
        yaxis_title="Hours"
    )

    return fig

# function to dynamically change what users can view based on their access level
def filter_by_access(df, staff_col="staff_member"):
    access = st.session_state.access_level
    username = st.session_state.username

    # Admins and viewers see everything
    if access in ("admin", "viewer"):
        return df

    # Users only see their own rows
    if access == "user":
        return df[df["username"] == username]

    # Safety fallback
    return df.iloc[0:0]

##### Functions to interact with SQLite database #####

from werkzeug.security import generate_password_hash
import pandas as pd


def update_staff_list(
    new_staff=None,
    job_role=None,
    hours_pw=None,
    leave_allowance_days=None,
    is_deployable=None,
    deploy_ratio=None,
    default_programme=None,
    username=None,
    password=None,
    user_access=None
    ):
    """
    Add or update a staff member in the Foundry staff_list dataset.
    """

    # Load current data
    staff_df = load_foundry_dataset("staff_list_0")

    # Hash password if supplied
    hashed_password = (
        generate_password_hash(password)
        if password
        else None
    )

    # Check whether staff member already exists
    existing_mask = (
        staff_df["staff_member"].astype(str).str.strip()
        == str(new_staff).strip()
    )

    if existing_mask.any():

        # --------------------------
        # UPDATE EXISTING RECORD
        # --------------------------

        staff_df.loc[existing_mask, "job_role"] = job_role
        staff_df.loc[existing_mask, "hours_pw"] = hours_pw
        staff_df.loc[existing_mask, "leave_allowance_days"] = leave_allowance_days
        staff_df.loc[existing_mask, "is_deployable"] = (
            int(is_deployable)
            if is_deployable is not None
            else None
        )
        staff_df.loc[existing_mask, "deploy_ratio"] = deploy_ratio
        staff_df.loc[existing_mask, "default_programme"] = default_programme
        staff_df.loc[existing_mask, "username"] = username
        staff_df.loc[existing_mask, "access_level"] = user_access

        # Only update password if supplied
        if hashed_password:
            staff_df.loc[
                existing_mask,
                "password"
            ] = hashed_password

        if "updated_at" in staff_df.columns:
            staff_df.loc[
                existing_mask,
                "updated_at"
            ] = pd.Timestamp.now()

    else:

        # --------------------------
        # CREATE NEW RECORD
        # --------------------------

        new_row = {
            "staff_member": new_staff,
            "job_role": job_role,
            "hours_pw": hours_pw,
            "leave_allowance_days": leave_allowance_days,
            "is_deployable": (
                int(is_deployable)
                if is_deployable is not None
                else 0
            ),
            "deploy_ratio": deploy_ratio,
            "archive_flag": 0,
            "username": username,
            "password": hashed_password,
            "access_level": user_access,
            "must_change_password": 1,
            "default_programme": default_programme,
            "created_at": pd.Timestamp.now(),
            "updated_at": pd.Timestamp.now()
        }

        staff_df = pd.concat(
            [
                staff_df,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

    # Save back to Foundry
    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    # Refresh cache if using Streamlit cache
    try:
        load_foundry_dataset.clear()
    except:
        pass

    return True
        
import pandas as pd


def update_programme_list(
    new_programme=None,
    programme_type=None,
    programme_group=None
):
    """
    Add a programme to the programme_categories Foundry dataset.

    Existing programmes are ignored (same behaviour as
    INSERT OR IGNORE in SQLite).
    """

    if not new_programme:
        return

    # Load current dataset
    programme_df = load_foundry_dataset(
        "programme_categories_0"
    )

    # Check if programme already exists
    exists = (
        programme_df["programme_categories"]
        .astype(str)
        .str.strip()
        .eq(str(new_programme).strip())
        .any()
    )

    # Mimic INSERT OR IGNORE
    if exists:
        return

    # Create new row
    new_row = {
        "programme_categories": new_programme,
        "programme_type": programme_type,
        "programme_group": programme_group,
        "archive_flag": 0
    }

    # Add row
    programme_df = pd.concat(
        [
            programme_df,
            pd.DataFrame([new_row])
        ],
        ignore_index=True
    )

    # Save back to Foundry
    save_foundry_dataset(
        "programme_categories_0",
        programme_df
    )

    # Clear cached copies if applicable
    try:
        load_foundry_dataset.clear()
    except:
        pass

from werkzeug.security import generate_password_hash
import pandas as pd


def update_password(username, new_password):
    """
    Update a user's password and clear
    the must_change_password flag.
    """

    # Load current staff dataset
    staff_df = load_foundry_dataset("staff_list_0")

    # Find user
    mask = (
        staff_df["username"]
        .astype(str)
        .str.strip()
        .eq(str(username).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Username '{username}' not found."
        )

    # Update password
    staff_df.loc[
        mask,
        "password"
    ] = generate_password_hash(new_password)

    # Clear forced password change flag
    staff_df.loc[
        mask,
        "must_change_password"
    ] = 0

    # Update timestamp if column exists
    if "updated_at" in staff_df.columns:
        staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    # Save back to Foundry
    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    # Clear cached dataset
    try:
        load_foundry_dataset.clear()
    except:
        pass

    return True

import pandas as pd


def restore_staff(staff_member):
    """
    Restore an archived staff member by setting
    archive_flag back to 0.
    """

    staff_df = load_foundry_dataset("staff_list_0")

    mask = (
        staff_df["staff_member"]
        .astype(str)
        .str.strip()
        .eq(str(staff_member).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Staff member '{staff_member}' not found."
        )

    staff_df.loc[
        mask,
        "archive_flag"
    ] = 0

    if "updated_at" in staff_df.columns:
        staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    try:
        load_foundry_dataset.clear()
    except:
        pass

    return True

def save_programme_activity(
    selected_staff,
    week_commencing,
    activity_inputs,
    repeat_weeks=1
):
    """
    Save programme activity for one or multiple weeks
    to the Foundry programme_activity dataset.
    """

    import pandas as pd
    from datetime import timedelta

    # Load existing activity dataset
    programme_df = load_foundry_dataset(
        "programme_activity_0"
    )

    base_week = pd.to_datetime(week_commencing)

    for week_offset in range(repeat_weeks):

        current_week = base_week + timedelta(
            weeks=week_offset
        )

        week_number = int(
            current_week.isocalendar().week
        )

        week_string = current_week.strftime(
            "%Y-%m-%d"
        )

        # ---------------------------------
        # DELETE EXISTING ENTRIES
        # ---------------------------------

        programme_df = programme_df[
            ~(
                (programme_df["staff_member"] == selected_staff)
                &
                (
                    programme_df["week_commencing"]
                    .astype(str)
                    .str[:10]
                    == week_string
                )
            )
        ]

        # ---------------------------------
        # INSERT NEW VALUES
        # ---------------------------------

        new_rows = []

        for programme, hours in activity_inputs.items():

            try:
                hours = float(hours)
            except:
                continue

            if hours <= 0:
                continue

            new_rows.append(
                {
                    "staff_member": selected_staff,
                    "programme_category": programme,
                    "activity_value": hours,
                    "week_commencing": week_string,
                    "week_number": week_number,
                }
            )

        if new_rows:

            programme_df = pd.concat(
                [
                    programme_df,
                    pd.DataFrame(new_rows)
                ],
                ignore_index=True
            )

    # Save updated dataset
    save_foundry_dataset(
        "programme_activity_0",
        programme_df
    )

    # Clear cache
    try:
        load_foundry_dataset.clear()
    except:
        pass

    return True

def save_annual_leave(
    staff_member,
    week_commencing,
    days_leave
):
    """
    Save annual leave to the leave_calendar Foundry dataset.

    Mimics:
    INSERT ... ON CONFLICT(staff_member, week_commencing)
    DO UPDATE
    """

    import pandas as pd

    week_commencing = pd.to_datetime(
        week_commencing
    )

    week_number = int(
        week_commencing.isocalendar().week
    )

    week_string = week_commencing.strftime(
        "%Y-%m-%d"
    )

    # Load existing dataset
    leave_df = load_foundry_dataset(
        "leave_calendar_0"
    )

    # Find existing record
    mask = (
        leave_df["staff_member"]
        .astype(str)
        .str.strip()
        .eq(str(staff_member).strip())
    ) & (
        leave_df["week_commencing"]
        .astype(str)
        .str[:10]
        .eq(week_string)
    )

    if mask.any():

        # --------------------------
        # UPDATE EXISTING RECORD
        # --------------------------

        leave_df.loc[
            mask,
            "days_leave"
        ] = days_leave

        leave_df.loc[
            mask,
            "week_number"
        ] = week_number

        if "updated_at" in leave_df.columns:
            leave_df.loc[
                mask,
                "updated_at"
            ] = pd.Timestamp.now()

    else:

        # --------------------------
        # INSERT NEW RECORD
        # --------------------------

        new_row = {
            "staff_member": staff_member,
            "week_commencing": week_string,
            "week_number": week_number,
            "days_leave": days_leave,
            "updated_at": pd.Timestamp.now()
        }

        leave_df = pd.concat(
            [
                leave_df,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

    # Save back to Foundry
    save_foundry_dataset(
        "leave_calendar_0",
        leave_df
    )

    # Clear cache
    try:
        load_foundry_dataset.clear()
    except:
        pass

    return True

def save_on_site(
    staff_member,
    programme_category,
    week_commencing,
    on_site_days
):
    """
    Save on-site days to the Foundry on_site_calendar dataset.

    Mimics:
    INSERT ... ON CONFLICT(staff_member,
                           programme_category,
                           week_commencing)
    DO UPDATE
    """

    import pandas as pd

    week_commencing = pd.to_datetime(
        week_commencing
    )

    week_number = int(
        week_commencing.isocalendar().week
    )

    week_string = week_commencing.strftime(
        "%Y-%m-%d"
    )

    # Load existing dataset
    onsite_df = load_foundry_dataset(
        "on_site_calendar_0"
    )

    # Find existing record
    mask = (
        onsite_df["staff_member"]
        .astype(str)
        .str.strip()
        .eq(str(staff_member).strip())
    ) & (
        onsite_df["programme_category"]
        .astype(str)
        .str.strip()
        .eq(str(programme_category).strip())
    ) & (
        onsite_df["week_commencing"]
        .astype(str)
        .str[:10]
        .eq(week_string)
    )

    if mask.any():

        # --------------------------
        # UPDATE EXISTING RECORD
        # --------------------------

        onsite_df.loc[
            mask,
            "on_site_days"
        ] = on_site_days

        onsite_df.loc[
            mask,
            "week_number"
        ] = week_number

        if "updated_at" in onsite_df.columns:
            onsite_df.loc[
                mask,
                "updated_at"
            ] = pd.Timestamp.now()

    else:

        # --------------------------
        # INSERT NEW RECORD
        # --------------------------

        new_row = {
            "staff_member": staff_member,
            "programme_category": programme_category,
            "week_commencing": week_string,
            "week_number": week_number,
            "on_site_days": on_site_days,
            "updated_at": pd.Timestamp.now()
        }

        onsite_df = pd.concat(
            [
                onsite_df,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

    # Save back to Foundry
    save_foundry_dataset(
        "on_site_calendar_0",
        onsite_df
    )

    # Clear cache
    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True

# ------------------------------------------------
# Helper function to create heatmaps
# ------------------------------------------------

def create_52week_heatmap(
    df,
    staff_col='staff_member',
    week_col='week_commencing',
    value_col='value',
    title="Staff Weekly Heatmap",
    colorscale="YlGnBu",
    colorbar_title="Value",
    zmax=None,
    highlight_current_week=True  # toggle highlight
    ):
    """
    Generates a 52-week heatmap for all staff with optional current week highlight
    and hover text disabled.
    """

    df = df.copy()

    # Convert week_col to datetime.date
    df[week_col] = pd.to_datetime(df[week_col], errors='coerce').dt.date

    # Generate 52 Mondays (26 back, 26 forward)
    today = date.today()
    start_monday = today - timedelta(weeks=26, days=today.weekday())
    week_commencings = [start_monday + timedelta(weeks=i) for i in range(52)]

    # Full staff × week grid
    staff_members = df[staff_col].unique()
    full_grid = pd.MultiIndex.from_product(
        [staff_members, week_commencings],
        names=[staff_col, week_col]
    ).to_frame(index=False)
    full_grid = full_grid.sort_values([staff_col, week_col]).reset_index(drop=True)
    full_grid['week_number'] = full_grid.groupby(staff_col).cumcount() + 1

    # Merge with existing data
    df_full = full_grid.merge(
        df[[staff_col, week_col, value_col]],
        on=[staff_col, week_col],
        how='left'
    )
    df_full[value_col] = df_full[value_col].fillna(0).astype(int)

    # Determine zmax
    if zmax is None:
        zmax = df_full[value_col].max()

    # Pivot for heatmap
    pivot = df_full.pivot_table(
    index=staff_col,
    columns=week_col,
    values=value_col,
    fill_value=0
    )

    # Remove unwanted axis labels like "undefined"
    pivot.index.name = None
    pivot.columns.name = None

    # Alternative safe method
    pivot = pivot.rename_axis(None, axis=0)
    pivot = pivot.rename_axis(None, axis=1)

    z = pivot.to_numpy()
    y = pivot.index.astype(str).tolist()
    cols = list(pivot.columns)
    x_vals = list(range(len(cols)))

    # Tick labels and current week index
    ticktext = []
    current_idx = None
    current_week_start = today - timedelta(days=today.weekday())

    for i, c in enumerate(cols):
        c_date = pd.to_datetime(c).date() if isinstance(c, str) else c
        ticktext.append(c_date.strftime("%d-%b-%y"))
        if highlight_current_week and c_date == current_week_start:
            current_idx = i

    # Build heatmap with hover disabled
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_vals,
            y=y,
            colorscale=colorscale,
            zmin=0,
            zmax=zmax,
            colorbar=dict(title=colorbar_title),
            hoverinfo='skip',       # disables hover
            hovertemplate=None       # ensures hover template is ignored
        )
    )

    fig.update_layout(
    title=title if title else "",
    xaxis=dict(
        tickmode="array",
        tickvals=x_vals,
        ticktext=ticktext,
        tickangle=90,
        title=None
    ),
    yaxis=dict(
        automargin=True,
        title=None
    ),
    margin=dict(l=160, r=20, t=40, b=120),
    height=max(350, pivot.shape[0] * 20 + 160),
    showlegend=False,
    )  

    # Highlight current week column fully behind heatmap
    shapes = []

    # Current week highlight
    if highlight_current_week and current_idx is not None:
        shapes.append(
            dict(
                type="rect",
                x0=current_idx - 0.5,
                x1=current_idx + 0.5,
                y0=-0.5,
                y1=len(y)-0.5,
                xref="x",
                yref="y",
                fillcolor="black",
                opacity=0.3,
                line_width=5,
                layer="above",
            )
        )

    # Subtle horizontal row separators
    for i in range(1, len(y)):
        shapes.append(
            dict(
                type="line",
                x0=-0.5,
                x1=len(x_vals) - 0.5,
                y0=i - 0.5,
                y1=i - 0.5,
                xref="x",
                yref="y",
                line=dict(
                    color="rgba(120,120,120,0.25)",
                    width=0.8
                ),
                layer="above"
            )
        )

    fig.update_layout(shapes=shapes)

    row_lines = []

    for i in range(1, len(y)):
        row_lines.append(
            dict(
                type="line",
                x0=-0.5,
                x1=len(x_vals) - 0.5,
                y0=i - 0.5,
                y1=i - 0.5,
                xref="x",
                yref="y",
                line=dict(
                    color="rgba(120,120,120,0.25)",
                    width=0.8
                ),
                layer="above"
            )
        )

    # Preserve existing shapes if present
    existing_shapes = list(fig.layout.shapes) if fig.layout.shapes else []
    fig.update_layout(shapes=existing_shapes + row_lines)

    return fig

def create_heatmap(
    df,
    value_col,
    title,
    colorscale,
    colorbar_title,
    zmax,
    current_week_start=None
    ):
    """Build a standardized Plotly heatmap used in dashboard pages."""
    MAX_DAYS = zmax
    if current_week_start is None:
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
    df = df.copy()
    df["week_commencing"] = pd.to_datetime(df["week_commencing"], errors="coerce").dt.date
    pivot = df.pivot_table(
        index="staff_member",
        columns="week_commencing",
        values=value_col,
        fill_value=0
    )
    z = pivot.to_numpy()
    y = pivot.index.astype(str).tolist()
    cols = list(pivot.columns)
    x_vals = list(range(len(cols)))
    ticktext = []
    current_idx = None
    for i, c in enumerate(cols):
        if hasattr(c, "date"):
            c_date = c.date()
            ticktext.append(c.strftime("%d-%b-%y"))
            if c_date == current_week_start:
                current_idx = i
        else:
            ticktext.append(str(c))
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_vals,
            y=y,
            colorscale=colorscale,
            zmin=0,
            zmax=MAX_DAYS,
            colorbar=dict(title=colorbar_title),
            customdata=[[c.strftime("%d-%b-%y") for c in cols]] * len(y),
            hovertemplate=(
                "Staff: %{y}<br>"
                "Week Commencing: %{customdata}<br>"
                f"{colorbar_title}: " + "%{z:.1f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=x_vals,
            ticktext=ticktext,
            tickangle=90,
        ),
        yaxis=dict(automargin=True),
        margin=dict(l=160, r=20, t=40, b=120),
        height=max(350, pivot.shape[0] * 20 + 160),
        showlegend=False,
    )
    if current_idx is not None:
        fig.add_vrect(
            x0=current_idx - 0.5,
            x1=current_idx + 0.5,
            xref="x",
            yref="paper",
            fillcolor="rgba(0,0,0,0.12)",
            opacity=0.15,
            line_width=2,
            line_color="black",
            layer="below",
        )
    return fig

def preview_colorscale(colorscale, title="Color Preview", n=100):
    """Show a horizontal bar preview of a given colorscale."""
    z = np.tile(np.linspace(0, 1, n), (10, 1))
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            colorscale=colorscale,
            showscale=False
        )
    )
    fig.update_layout(
        title={"text": title, "x": 0.5},
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        height=100,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

def clean_programme(text):
    if pd.isna(text):
        return text

    # Step 1: Replace standalone "and" with "&" (case-insensitive)
    text = re.sub(r'\band\b', '&', text, flags=re.IGNORECASE)

    # Step 2: Split text into words
    words = text.split()

    cleaned_words = []
    for w in words:
        # If word is all uppercase (acronym), keep it as is
        if w.isupper():
            cleaned_words.append(w)
        else:
            # Otherwise capitalize first letter
            cleaned_words.append(w.capitalize())

    return ' '.join(cleaned_words)

def get_weekly_data_entry_status(
    staff_list,
    programme_calendar_df,
    leave_calendar_df,
    week_commencing
    ):
    """
    Returns a staff-level checklist showing whether each staff member
    has entered programme activity for the selected week.
    """

    import pandas as pd

    # -----------------------------
    # Standardise week format
    # -----------------------------
    week_commencing = pd.to_datetime(week_commencing).date()

    programme_calendar_df = programme_calendar_df.copy()
    leave_calendar_df = leave_calendar_df.copy()

    programme_calendar_df["week_commencing"] = pd.to_datetime(
        programme_calendar_df["week_commencing"]
    ).dt.date

    leave_calendar_df["week_commencing"] = pd.to_datetime(
        leave_calendar_df["week_commencing"]
    ).dt.date

    # -----------------------------
    # Active staff only
    # -----------------------------
    df = staff_list.loc[
        staff_list["archive_flag"] == 0,
        ["staff_member"]
    ].copy()

    # -----------------------------
    # WHO HAS ENTERED PROGRAMME DATA
    # -----------------------------
    entered_staff = programme_calendar_df.loc[
        programme_calendar_df["week_commencing"] == week_commencing,
        "staff_member"
    ].dropna().unique()

    df["has_entered"] = df["staff_member"].isin(entered_staff)

    # -----------------------------
    # OPTIONAL: leave context (not blocking entry flag)
    # -----------------------------
    leave_summary = leave_calendar_df.loc[
        leave_calendar_df["week_commencing"] == week_commencing
    ].copy()

    if not leave_summary.empty:
        leave_summary = (
            leave_summary.groupby("staff_member")["days_leave"]
            .sum()
            .reset_index()
        )
    else:
        leave_summary = pd.DataFrame(columns=["staff_member", "days_leave"])

    df = df.merge(leave_summary, on="staff_member", how="left")
    df["days_leave"] = df["days_leave"].fillna(0)

    df["on_full_leave"] = df["days_leave"] >= 5

    # -----------------------------
    # STATUS LOGIC
    # -----------------------------
    def get_status(row):
        if row["has_entered"]:
            return "Entered"
        elif row["on_full_leave"]:
            return "On Leave"
        else:
            return "Missing"

    df["status"] = df.apply(get_status, axis=1)

    # -----------------------------
    # PRIORITY FLAG (for sorting / red highlighting)
    # -----------------------------
    df["needs_attention"] = ~df["has_entered"] & ~df["on_full_leave"]

    # -----------------------------
    # SORT: missing first
    # -----------------------------
    df = df.sort_values(
        ["needs_attention", "staff_member"],
        ascending=[False, True]
    ).reset_index(drop=True)

    # -----------------------------
    # CLEAN OUTPUT FOR UI
    # -----------------------------

    df["days_leave"] = df["days_leave"].fillna(0)

    # round to nearest 0.5 day
    df["days_leave"] = (df["days_leave"] * 2).round() / 2

    df_clean = df.rename(columns={
        "staff_member": "Staff Member",
        "days_leave": "Days Leave",
        "status": "Status"
    })[["Staff Member", "Days Leave", "Status"]]

    return df_clean

def render_data_entry_checklist(df_flags):

    import streamlit as st

    st.subheader("📋 Data Entry Checklist")

    def colour_row(row):

        if row["Status"] == "Entered":
            return ["background-color: #d4edda"] * len(row)

        elif row["Status"] == "On Leave":
            return ["background-color: #fff3cd"] * len(row)

        else:
            return ["background-color: #f8d7da"] * len(row)

    st.dataframe(
        df_flags.style.apply(colour_row, axis=1),
        use_container_width=True,
        hide_index=True
    )

    missing = (df_flags["Status"] == "Missing").sum()

    on_leave = (df_flags["Status"] == "On Leave").sum()

    if missing == 0:
        st.success("✅ All staff have entered data for this week")
    else:
        st.warning(f"⚠️ {missing} staff still need to enter data")

    if on_leave > 0:
        st.info(f"🏖 {on_leave} staff are on full-week leave")

# ============================
# DEFAULT PROGRAMME HELPERS
# ============================

def clean_default_programme_column(staff_df, programme_df):
    """
    Ensures default_programme exists, is cleaned, and valid.
    """
    df = staff_df.copy()

    if "default_programme" not in df.columns:
        df["default_programme"] = None

    df["default_programme"] = (
        df["default_programme"]
        .astype(str)
        .str.strip()
        .replace({"": None, "nan": None})
    )

    valid_programmes = set(
        programme_df["programme_categories"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    df["default_programme"] = df["default_programme"].apply(
        lambda x: x if x in valid_programmes else None
    )

    return df


def get_default_programme_map(staff_df):
    return dict(zip(staff_df["staff_member"], staff_df["default_programme"]))


def get_deployable_hours_map(staff_df):
    df = staff_df.copy()
    df["hours_pw"] = df["hours_pw"].fillna(37.5)
    df["deploy_ratio"] = df["deploy_ratio"].fillna(1.0)
    df["deployable_hours"] = df["hours_pw"] * df["deploy_ratio"]
    return dict(zip(df["staff_member"], df["deployable_hours"]))


def calculate_default_hours_for_staff(staff_df, staff_member, pct=1.0):
    """
    Calculates default hours based on deployable capacity.
    """
    row = staff_df.loc[staff_df["staff_member"] == staff_member]

    if row.empty:
        return 0.0

    hours_pw = float(row.iloc[0].get("hours_pw", 37.5) or 37.5)
    deploy_ratio = float(row.iloc[0].get("deploy_ratio", 1.0) or 1.0)

    deployable_hours = hours_pw * deploy_ratio

    return round(deployable_hours * pct, 1)


# ============================
# CAPACITY CALCULATIONS
# ============================

def build_staff_week_capacity(prog_df, leave_df, staff_df):
    """
    Builds staff-week capacity table.
    """
    prog_staff_week = (
        prog_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(total_prog_hours=("activity_value", "sum"))
    )

    leave_df = leave_df.copy()
    leave_df["leave_hours"] = leave_df["days_leave"].fillna(0) * 7.5

    leave_staff_week = (
        leave_df
        .groupby(["staff_member", "week_commencing"], as_index=False)
        .agg(total_leave_hours=("leave_hours", "sum"))
    )

    staff_base = staff_df[["staff_member", "hours_pw", "deploy_ratio"]].copy()

    staff_week = prog_staff_week.merge(
        leave_staff_week,
        on=["staff_member", "week_commencing"],
        how="outer"
    ).merge(
        staff_base,
        on="staff_member",
        how="left"
    )

    staff_week = staff_week.fillna({
        "total_prog_hours": 0,
        "total_leave_hours": 0,
        "deploy_ratio": 1.0,
        "hours_pw": 37.5
    })

    staff_week["total_contr_hours"] = staff_week["hours_pw"]
    staff_week["total_avail_hours"] = (
        (staff_week["total_contr_hours"] - staff_week["total_leave_hours"]) * (1 - staff_week["deploy_ratio"])
    ).clip(lower=0)

    staff_week["total_non_deploy_hours"] = (
        staff_week["total_avail_hours"] * (1 - staff_week["deploy_ratio"])
    )

    staff_week["total_util_hours"] = (
        staff_week["total_prog_hours"] + staff_week["total_non_deploy_hours"]
    )

    return staff_week


def build_weekly_summary(staff_week, target_util_rate):
    weekly = (
        staff_week
        .groupby("week_commencing", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
        )
        .sort_values("week_commencing")
    )

    weekly["util_rate"] = (
        (weekly["total_non_deploy_hours"] + weekly["total_prog_hours"])
        / weekly["total_avail_hours"]
        * 100
    ).fillna(0)

    weekly["util_target"] = target_util_rate

    return weekly


def build_monthly_summary(staff_week, weekly):
    weekly_by_staff = (
        staff_week
        .groupby(["staff_member","week_commencing"], as_index=False)
        .sum(numeric_only=True)
    )

    monthly = weekly.copy()
    monthly["month"] = monthly["week_commencing"].dt.to_period("M").dt.to_timestamp()

    monthly_by_staff = weekly_by_staff.copy()
    monthly_by_staff["month"] = monthly_by_staff["week_commencing"].dt.to_period("M").dt.to_timestamp()

    monthly_by_staff = (
        monthly_by_staff
        .groupby(["staff_member","month"], as_index=False)
        .sum(numeric_only=True)
    )

    return monthly_by_staff

def handle_trigger_reload():
    """
    Centralised reload handler for Streamlit session state triggers.
    Calls appropriate data refresh functions in data_store.
    """

    trigger = st.session_state.get("trigger_reload")

    if not trigger:
        return

    if trigger == "leave":
        refresh_leave_calendar()

    elif trigger == "onsite":
        refresh_onsite_calendar()

    elif trigger == "programme":
        refresh_programme_activity()

    elif trigger == "all":
        ds.load_or_refresh_all()

    # Clear trigger after handling
    del st.session_state["trigger_reload"]

def reset_all_passwords(
    temp_password="Temporary123!",
    only_if_null=False
    ):
    """
    Resets passwords for staff in the Foundry dataset.

    Args:
        temp_password (str):
            Password to apply.

        only_if_null (bool):
            If True, only reset users with
            a blank or null password.
    """

    staff_df = load_foundry_dataset(
        "staff_list_0"
    )

    if only_if_null:

        mask = (
            staff_df["password"].isna()
            |
            (
                staff_df["password"]
                .astype(str)
                .str.strip()
                == ""
            )
        )

    else:

        mask = pd.Series(
            True,
            index=staff_df.index
        )

    # Generate a unique salted hash
    # for each affected user
    for idx in staff_df.loc[mask].index:

        staff_df.loc[
            idx,
            "password"
        ] = generate_password_hash(
            temp_password
        )

    # Force password change
    staff_df.loc[
        mask,
        "must_change_password"
    ] = 1

    # Update timestamp if available
    if "updated_at" in staff_df.columns:

        staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    # Save back to Foundry
    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    # Clear cached copy
    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True

def reset_passwords_from_dataframe(
    staff_df,
    temp_password="Temporary123!"
):
    """
    Reset passwords for staff members contained
    in the supplied dataframe.
    """

    # Load current staff dataset
    current_staff_df = load_foundry_dataset(
        "staff_list_0"
    )

    staff_members_to_update = (
        staff_df["staff_member"]
        .astype(str)
        .str.strip()
        .tolist()
    )

    mask = current_staff_df["staff_member"].astype(
        str
    ).str.strip().isin(
        staff_members_to_update
    )

    # Generate unique salted hash for each user
    for idx in current_staff_df.loc[mask].index:

        current_staff_df.loc[
            idx,
            "password"
        ] = generate_password_hash(
            temp_password
        )

    current_staff_df.loc[
        mask,
        "must_change_password"
    ] = 1

    if "updated_at" in current_staff_df.columns:

        current_staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    # Save back to Foundry
    save_foundry_dataset(
        "staff_list_0",
        current_staff_df
    )

    # Clear cache
    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
def build_monthly_capacity_df(staff_week_df, target_util_rate=85):
    """
    Builds monthly capacity summary from staff_week_capacity_df
    """

    if staff_week_df is None or staff_week_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # ---------------------------
    # Weekly base
    # ---------------------------
    weekly = (
        staff_week_df
        .groupby("week_commencing", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
            staff_count=("staff_member", "nunique"),
        )
        .sort_values("week_commencing")
    )

    weekly["util_rate"] = (
        (weekly["total_non_deploy_hours"] + weekly["total_prog_hours"])
        / weekly["total_avail_hours"]
        * 100
    ).fillna(0)

    weekly["util_target"] = target_util_rate

    # ---------------------------
    # Monthly (overall)
    # ---------------------------
    weekly["month"] = weekly["week_commencing"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        weekly
        .groupby("month", as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
            staff_count=("staff_count", "mean"),
        )
        .sort_values("month")
    )

    # ---------------------------
    # Monthly by staff
    # ---------------------------
    staff_week_df["month"] = staff_week_df["week_commencing"].dt.to_period("M").dt.to_timestamp()

    monthly_by_staff = (
        staff_week_df
        .groupby(["staff_member", "month"], as_index=False)
        .agg(
            total_leave_hours=("total_leave_hours", "sum"),
            total_contr_hours=("total_contr_hours", "sum"),
            total_avail_hours=("total_avail_hours", "sum"),
            total_prog_hours=("total_prog_hours", "sum"),
            total_non_deploy_hours=("total_non_deploy_hours", "sum"),
            total_util_hours=("total_util_hours", "sum"),
        )
        .sort_values("month")
    )

    # ---------------------------
    # Util %
    # ---------------------------
    monthly["util_rate"] = (
        (monthly["total_non_deploy_hours"] + monthly["total_prog_hours"])
        / monthly["total_avail_hours"]
        * 100
    ).fillna(0)

    monthly["util_target"] = target_util_rate

    # ---------------------------
    # Filter to latest 12 months
    # ---------------------------
    latest_month = monthly["month"].max()
    start_month = latest_month - pd.DateOffset(months=11)
    year_month = '2025-01-01'

    monthly = monthly[
        monthly["month"].between(year_month, latest_month)
    ]

    monthly_by_staff = monthly_by_staff[
        monthly_by_staff["month"].between(start_month, latest_month)
    ]

    return monthly, monthly_by_staff

def refresh_leave_calendar():
    
    load_foundry_dataset.clear()

    leave_df = load_foundry_dataset(
        "leave_calendar_0"
    )

    leave_df["week_commencing"] = pd.to_datetime(
        leave_df["week_commencing"],
        errors="coerce"
    )

    st.session_state.leave_calendar_df = leave_df
    
def refresh_onsite_calendar():
    
    load_foundry_dataset.clear()

    onsite_df = load_foundry_dataset(
        "on_site_calendar_0"
    )

    onsite_df = (
        onsite_df
        .groupby(
            [
                "staff_member",
                "week_commencing",
                "week_number"
            ],
            as_index=False
        )["on_site_days"]
        .sum()
    )

    onsite_df["week_commencing"] = pd.to_datetime(
        onsite_df["week_commencing"],
        errors="coerce"
    )

    st.session_state.onsite_calendar_df = onsite_df
    
def refresh_programme_activity():
    
    load_foundry_dataset.clear()

    programme_df = load_foundry_dataset(
        "programme_activity_0"
    )

    programme_df["week_commencing"] = pd.to_datetime(
        programme_df["week_commencing"],
        errors="coerce"
    )

    st.session_state.programme_calendar_df = programme_df
    
def load_foundry_dataset(alias):
    ds = Dataset.get(alias)
    file = list(ds.files())[0]
    local_path = file.download()
    return pd.read_csv(local_path)


def save_foundry_dataset(alias, df):
    ds = Dataset.get(alias)

    # clear cached version before write
    load_foundry_dataset.clear()

    ds.write_table(df)

    # clear again so next read gets latest data
    load_foundry_dataset.clear()

def stream_data():
    for ch in login_prompt:
        yield ch
        time.sleep(0.02)
        
def archive_staff(staff_member):

    staff_df = load_foundry_dataset("staff_list_0")

    mask = (
        staff_df["staff_member"]
        == staff_member
    )

    staff_df.loc[
        mask,
        "archive_flag"
    ] = 1

    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    load_foundry_dataset.clear()
    
def update_access_level(
    staff_member,
    access_level
    ):
    """
    Update a staff member's access level.
    """

    staff_df = load_foundry_dataset(
        "staff_list_0"
    )

    mask = (
        staff_df["staff_member"]
        .astype(str)
        .str.strip()
        .eq(str(staff_member).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Staff member '{staff_member}' not found."
        )

    staff_df.loc[
        mask,
        "access_level"
    ] = access_level

    if "updated_at" in staff_df.columns:
        staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
    
def archive_programme(programme_name):
    """
    Archive a programme category by setting
    archive_flag = 1.
    """

    programme_df = load_foundry_dataset(
        "programme_categories_0"
    )

    mask = (
        programme_df["programme_categories"]
        .astype(str)
        .str.strip()
        .eq(str(programme_name).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Programme '{programme_name}' not found."
        )

    programme_df.loc[
        mask,
        "archive_flag"
    ] = 1

    if "updated_at" in programme_df.columns:
        programme_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "programme_categories_0",
        programme_df
    )

    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
    
def restore_programme(programme_name):
    """
    Restore an archived programme category by setting
    archive_flag = 0.
    """

    programme_df = load_foundry_dataset(
        "programme_categories_0"
    )

    mask = (
        programme_df["programme_categories"]
        .astype(str)
        .str.strip()
        .eq(str(programme_name).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Programme '{programme_name}' not found."
        )

    programme_df.loc[
        mask,
        "archive_flag"
    ] = 0

    if "updated_at" in programme_df.columns:
        programme_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "programme_categories_0",
        programme_df
    )

    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
    
def update_programme_group(
    programme_name,
    programme_group
):
    """
    Update the programme group
    for a programme category.
    """

    programme_df = load_foundry_dataset(
        "programme_categories_0"
    )

    mask = (
        programme_df["programme_categories"]
        .astype(str)
        .str.strip()
        .eq(str(programme_name).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Programme '{programme_name}' not found."
        )

    programme_df.loc[
        mask,
        "programme_group"
    ] = programme_group

    if "updated_at" in programme_df.columns:
        programme_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "programme_categories_0",
        programme_df
    )

    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
    
def delete_programme(programme_name):
    """
    Permanently delete a programme category.
    """

    programme_df = load_foundry_dataset(
        "programme_categories_0"
    )

    programme_df = programme_df[
        programme_df["programme_categories"]
        != programme_name
    ]

    save_foundry_dataset(
        "programme_categories_0",
        programme_df
    )

    try:
        load_foundry_dataset.clear()
    except Exception:
        pass

    return True
    
def reset_individual_password(
    username,
    temp_password
):

    staff_df = load_foundry_dataset(
        "staff_list_0"
    )

    mask = (
        staff_df["username"]
        .astype(str)
        .str.strip()
        .eq(str(username).strip())
    )

    if not mask.any():
        raise ValueError(
            f"Username '{username}' not found"
        )

    staff_df.loc[
        mask,
        "password"
    ] = generate_password_hash(
        temp_password
    )

    staff_df.loc[
        mask,
        "must_change_password"
    ] = 1

    if "updated_at" in staff_df.columns:
        staff_df.loc[
            mask,
            "updated_at"
        ] = pd.Timestamp.now()

    save_foundry_dataset(
        "staff_list_0",
        staff_df
    )

    load_foundry_dataset.clear()
