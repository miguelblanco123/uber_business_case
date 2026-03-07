"""Compute KPI scalar metrics from the filtered ATD DataFrame."""
import pandas as pd

SLA_THRESHOLD_MIN: int = 45


def compute_kpis(df: pd.DataFrame) -> dict:
    """Return a dict of 5 KPI scalars for the dashboard header row.

    Args:
        df: Filtered DataFrame (may be empty).

    Returns:
        Dict with keys: total_trips, sla_rate, mean_atd,
        active_drivers, median_atd.
        All values are zero/0.0 when *df* is empty.
    """
    if df.empty:
        return {
            "total_trips": 0,
            "sla_rate": 0.0,
            "mean_atd": 0.0,
            "active_drivers": 0,
            "median_atd": 0.0,
        }

    total = len(df)
    sla_count = (df["ATD"] <= SLA_THRESHOLD_MIN).sum()

    return {
        "total_trips": total,
        "sla_rate": round(100.0 * sla_count / total, 1),
        "mean_atd": round(df["ATD"].mean(), 1),
        "active_drivers": df["driver_uuid"].nunique(),
        "median_atd": round(df["ATD"].median(), 1),
    }
