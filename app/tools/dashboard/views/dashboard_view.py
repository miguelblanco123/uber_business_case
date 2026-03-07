"""Main dashboard orchestrator — sidebar filters + tab layout."""
import datetime
import os

import streamlit as st

from tools.dashboard.data.loader import load_data
from tools.dashboard.services.filters import apply_filters
from tools.dashboard.services.metrics import compute_kpis
from tools.dashboard.views.delivery_analysis import (
    render_delivery_analysis,
)
from tools.dashboard.views.geo_analysis import render_geo_analysis
from tools.dashboard.views.kpi_cards import render_kpi_cards
from tools.dashboard.views.sla_analysis import render_sla_analysis
from tools.dashboard.views.time_analysis import render_time_analysis

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.normpath(
    os.path.join(
        _HERE, "..", "..", "..", "..",
        "data", "processed", "preprocessed.parquet",
    )
)

_TAB_NAMES = [
    "Performance Overview",
    "Time Patterns",
    "Courier & Platform",
    "Geographic",
]


def _monday_weeks(
    min_date: datetime.date,
    max_date: datetime.date,
) -> list:
    """Return (monday, sunday) pairs for every week in the range.

    Weeks start on Monday. The last pair is clamped to max_date.
    """
    # days forward from min_date to the next (or same) Monday
    # weekday(): Mon=0 … Sun=6
    days_fwd = (-min_date.weekday()) % 7
    first_mon = min_date + datetime.timedelta(days=days_fwd)
    weeks = []
    cur = first_mon
    while cur <= max_date:
        end = min(cur + datetime.timedelta(days=6), max_date)
        weeks.append((cur, end))
        cur += datetime.timedelta(days=7)
    return weeks


def _week_label(start: datetime.date, end: datetime.date) -> str:
    """Format a week pair as a human-readable selectbox label."""
    label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    if (end - start).days < 6:
        label += " (partial)"
    return label


def dashboard_view() -> None:
    """Render the full ATD analytics dashboard.

    Loads data from the preprocessed parquet, builds sidebar filters,
    computes KPIs, and delegates each tab to its view module.
    """
    full_df = load_data(DATA_PATH)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("---")
        st.subheader("Filters")

        min_date = full_df["date"].min()
        max_date = full_df["date"].max()

        # Build Monday-starting week options
        weeks = _monday_weeks(min_date, max_date)
        week_labels = [_week_label(s, e) for s, e in weeks]
        week_map = dict(zip(week_labels, weeks))

        selected_label = st.selectbox(
            "Week (Mon – Sun)",
            options=week_labels,
            index=len(week_labels) - 1,  # default: most recent week
        )
        date_start, date_end = week_map[selected_label]

        all_territories = sorted(
            full_df["territory"].dropna().unique().tolist()
        )
        all_flows = sorted(
            full_df["courier_flow"].dropna().unique().tolist()
        )
        all_archetypes = sorted(
            full_df["geo_archetype"].dropna().unique().tolist()
        )

        territories = st.multiselect(
            "Territory",
            options=all_territories,
            default=all_territories,
        )
        courier_flows = st.multiselect(
            "Courier Flow",
            options=all_flows,
            default=all_flows,
        )
        geo_archetypes = st.multiselect(
            "Geo Archetype",
            options=all_archetypes,
            default=all_archetypes,
        )
        atd_range = st.slider(
            "ATD Range (min)",
            min_value=0,
            max_value=120,
            value=(0, 120),
        )

        week_df = full_df[
            (full_df["date"] >= date_start)
            & (full_df["date"] <= date_end)
        ]
        filtered_df = apply_filters(
            week_df,
            territories=territories,
            courier_flows=courier_flows,
            geo_archetypes=geo_archetypes,
            atd_min=float(atd_range[0]),
            atd_max=float(atd_range[1]),
        )
        st.caption(f"{len(filtered_df):,} trips match filters")

    # --- Main area ---
    st.title("Uber Eats Mexico — ATD Analytics")

    if len(filtered_df) == 0:
        st.error(
            "No trips match the current filter selection. "
            "Please broaden your filters."
        )
        return

    # Previous week KPIs (same duration, 7 days earlier)
    span = (date_end - date_start).days + 1
    prev_end = date_start - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=span - 1)
    prev_filtered_df = apply_filters(
        full_df[
            (full_df["date"] >= prev_start)
            & (full_df["date"] <= prev_end)
        ],
        territories=territories,
        courier_flows=courier_flows,
        geo_archetypes=geo_archetypes,
        atd_min=float(atd_range[0]),
        atd_max=float(atd_range[1]),
    )

    # All-time filtered df (for historic ATD baseline in Time Patterns)
    historic_df = apply_filters(
        full_df,
        territories=territories,
        courier_flows=courier_flows,
        geo_archetypes=geo_archetypes,
        atd_min=float(atd_range[0]),
        atd_max=float(atd_range[1]),
    )

    kpis = compute_kpis(filtered_df)
    prev_kpis = compute_kpis(prev_filtered_df)
    render_kpi_cards(kpis, prev_kpis)

    tabs = st.tabs(_TAB_NAMES)

    with tabs[0]:
        render_sla_analysis(filtered_df)

    with tabs[1]:
        render_time_analysis(filtered_df, historic_df)

    with tabs[2]:
        render_delivery_analysis(filtered_df)

    with tabs[3]:
        render_geo_analysis(filtered_df)
