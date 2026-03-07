"""Render the top KPI metric row with WoW deltas."""
import streamlit as st


def _fmt_count(n: int) -> str:
    """Format an integer count with K / M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _delta_count(curr: int, prev: int) -> str | None:
    """Return a signed K/M delta string, or None when no prev data."""
    if prev == 0:
        return None
    diff = curr - prev
    sign = "+" if diff >= 0 else ""
    return f"{sign}{_fmt_count(abs(diff))}" if diff != 0 else "0"


def _delta_float(curr: float, prev: float, unit: str = "") -> str | None:
    """Return a signed float delta string, or None when no prev data."""
    if prev == 0.0:
        return None
    diff = round(curr - prev, 1)
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff}{unit}"


def render_kpi_cards(kpis: dict, prev_kpis: dict) -> None:
    """Display 5 KPI metrics with week-over-week deltas.

    Args:
        kpis: Current-week KPIs from ``metrics.compute_kpis``.
        prev_kpis: Previous-week KPIs for delta comparison.
    """
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Mean ATD (min)",
        value=f"{kpis['mean_atd']:.1f}",
        delta=_delta_float(
            kpis["mean_atd"], prev_kpis["mean_atd"], " min"
        ),
        delta_color="inverse",   # lower ATD = better
    )
    c2.metric(
        "Median ATD (min)",
        value=f"{kpis['median_atd']:.1f}",
        delta=_delta_float(
            kpis["median_atd"], prev_kpis["median_atd"], " min"
        ),
        delta_color="inverse",   # lower ATD = better
    )
    c3.metric(
        "SLA Rate",
        value=f"{kpis['sla_rate']:.1f}%",
        delta=_delta_float(
            kpis["sla_rate"], prev_kpis["sla_rate"], " pp"
        ),
        help="% trips with ATD ≤ 45 min. Delta in percentage points.",
    )
    c4.metric(
        "Total Trips",
        value=_fmt_count(kpis["total_trips"]),
        delta=_delta_count(
            kpis["total_trips"], prev_kpis["total_trips"]
        ),
    )
    c5.metric(
        "Active Drivers",
        value=_fmt_count(kpis["active_drivers"]),
        delta=_delta_count(
            kpis["active_drivers"], prev_kpis["active_drivers"]
        ),
    )
