"""All groupby aggregations for dashboard charts.

No Streamlit imports — pure pandas/numpy only.
"""
import numpy as np
import pandas as pd

_DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

_ALL_HOURS = list(range(24))


def atd_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Return raw ATD values with percentile metadata.

    The returned DataFrame has a single column ``ATD``.
    ``df.attrs`` carries keys ``p25``, ``p50``, ``p75``.
    """
    out = df[["ATD"]].dropna().copy()
    out.attrs["p25"] = float(np.percentile(out["ATD"], 25))
    out.attrs["p50"] = float(np.percentile(out["ATD"], 50))
    out.attrs["p75"] = float(np.percentile(out["ATD"], 75))
    return out


def sla_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Return trip counts and percentages for 4 SLA buckets.

    Buckets: ``<30 min``, ``30-45 min``, ``45-60 min``, ``>60 min``.
    """
    labels = ["<30 min", "30-45 min", "45-60 min", ">60 min"]
    bins = [0, 30, 45, 60, float("inf")]
    cuts = pd.cut(
        df["ATD"].dropna(),
        bins=bins,
        labels=labels,
        right=True,
    )
    counts = cuts.value_counts().reindex(labels, fill_value=0)
    total = counts.sum()
    pct = (100.0 * counts / total).round(1) if total > 0 else counts * 0.0
    return pd.DataFrame(
        {"bucket": labels, "count": counts.values, "pct": pct.values}
    )


def atd_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean ATD and trip count for each local hour (0-23)."""
    grp = (
        df.groupby("hour_local", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reindex(_ALL_HOURS, fill_value=np.nan)
        .reset_index()
    )
    grp.columns = ["hour_local", "mean_atd", "trip_count"]
    grp["trip_count"] = grp["trip_count"].fillna(0).astype(int)
    return grp


def trips_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Return trip volume for each local hour (0-23), zero-filled."""
    counts = (
        df.groupby("hour_local", observed=True)
        .size()
        .reindex(_ALL_HOURS, fill_value=0)
        .reset_index(name="trip_count")
    )
    return counts


def atd_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Return a 7×24 pivot of mean ATD (day_name × hour_local).

    Missing cells are NaN. Rows ordered Mon-Sun.
    """
    pivot = df.pivot_table(
        values="ATD",
        index="day_name",
        columns="hour_local",
        aggfunc="mean",
    )
    pivot = pivot.reindex(index=_DAY_ORDER, columns=_ALL_HOURS)
    return pivot


def atd_by_courier_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean ATD and trip count per courier_flow, asc by ATD."""
    grp = (
        df.groupby("courier_flow", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reset_index()
        .sort_values("mean_atd")
    )
    grp.columns = ["courier_flow", "mean_atd", "trip_count"]
    return grp


def trips_by_courier_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Return trip count per courier_flow, descending."""
    counts = (
        df.groupby("courier_flow", observed=True)
        .size()
        .reset_index(name="trip_count")
        .sort_values("trip_count", ascending=False)
    )
    return counts


def atd_by_merchant_surface(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean ATD and trip count per merchant_surface, asc ATD."""
    grp = (
        df.groupby("merchant_surface", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reset_index()
        .sort_values("mean_atd")
    )
    grp.columns = ["merchant_surface", "mean_atd", "trip_count"]
    return grp


def atd_by_territory(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean ATD and trip count per territory, asc by ATD."""
    grp = (
        df.groupby("territory", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reset_index()
        .sort_values("mean_atd")
    )
    grp.columns = ["territory", "mean_atd", "trip_count"]
    return grp


def trips_by_territory(df: pd.DataFrame) -> pd.DataFrame:
    """Return trip count per territory, descending."""
    counts = (
        df.groupby("territory", observed=True)
        .size()
        .reset_index(name="trip_count")
        .sort_values("trip_count", ascending=False)
    )
    return counts


def atd_by_geo_archetype(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean ATD and trip count per geo_archetype, asc ATD."""
    grp = (
        df.groupby("geo_archetype", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reset_index()
        .sort_values("mean_atd")
    )
    grp.columns = ["geo_archetype", "mean_atd", "trip_count"]
    return grp


def atd_by_distance_bins(
    df: pd.DataFrame,
    col: str,
    n_bins: int = 5,
) -> pd.DataFrame:
    """Return mean ATD per distance quantile bin for *col*.

    Args:
        df: Filtered DataFrame.
        col: Distance column name (e.g. ``pickup_distance``).
        n_bins: Number of quantile bins.

    Returns:
        DataFrame with columns ``bin_label``, ``mean_atd``,
        ``trip_count``.
    """
    sub = df[[col, "ATD"]].dropna()
    if sub.empty:
        return pd.DataFrame(
            columns=["bin_label", "mean_atd", "trip_count"]
        )
    sub = sub.copy()
    sub["bin"] = pd.qcut(
        sub[col], q=n_bins, duplicates="drop"
    )
    grp = (
        sub.groupby("bin", observed=True)["ATD"]
        .agg(mean_atd="mean", trip_count="count")
        .reset_index()
    )
    grp["bin_label"] = grp["bin"].astype(str)
    return grp[["bin_label", "mean_atd", "trip_count"]]


def scatter_distance_atd(
    df: pd.DataFrame,
    sample_size: int = 5000,
) -> pd.DataFrame:
    """Return a random sample for a distance vs ATD scatter plot.

    Returns columns: ``total_distance``, ``ATD``, ``courier_flow``.
    """
    sub = df[["total_distance", "ATD", "courier_flow"]].dropna()
    if len(sub) > sample_size:
        sub = sub.sample(n=sample_size, random_state=42)
    return sub.reset_index(drop=True)


def sample_courier_flow_atd(
    df: pd.DataFrame,
    n: int = 20000,
) -> pd.DataFrame:
    """Return a random sample of courier_flow and ATD for box plots.

    Args:
        df: Filtered DataFrame.
        n: Maximum number of rows to return.

    Returns:
        DataFrame with columns ``courier_flow``, ``ATD``.
    """
    sub = df[["courier_flow", "ATD"]].dropna()
    if len(sub) > n:
        sub = sub.sample(n=n, random_state=42)
    return sub.reset_index(drop=True)


def sla_rate_by_courier_flow(
    df: pd.DataFrame,
    sla_min: float = 45.0,
) -> pd.DataFrame:
    """Return SLA pass rate per courier_flow.

    Args:
        df: Filtered DataFrame.
        sla_min: SLA threshold in minutes.

    Returns:
        DataFrame with columns ``courier_flow``,
        ``sla_rate``, ``trip_count``, ``mean_atd``,
        sorted descending by ``sla_rate``.
    """
    sub = df[["courier_flow", "ATD"]].dropna().copy()
    sub["within_sla"] = sub["ATD"] <= sla_min
    grp = (
        sub.groupby("courier_flow", observed=True)
        .agg(
            trip_count=("ATD", "count"),
            mean_atd=("ATD", "mean"),
            sla_pass=("within_sla", "sum"),
        )
        .reset_index()
    )
    grp["sla_rate"] = (
        100.0 * grp["sla_pass"] / grp["trip_count"]
    ).round(1)
    return grp[
        ["courier_flow", "sla_rate", "trip_count", "mean_atd"]
    ].sort_values("sla_rate", ascending=False)


def sla_buckets_by_merchant_surface(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Return SLA bucket breakdown per merchant_surface.

    Args:
        df: Filtered DataFrame.

    Returns:
        Long-format DataFrame with columns
        ``merchant_surface``, ``bucket``, ``count``, ``pct``.
        Percentages are within each merchant_surface.
    """
    labels = ["<30 min", "30-45 min", "45-60 min", ">60 min"]
    bins = [0, 30, 45, 60, float("inf")]
    sub = df[["merchant_surface", "ATD"]].dropna().copy()
    sub["bucket"] = pd.cut(
        sub["ATD"], bins=bins, labels=labels, right=True
    )
    grp = (
        sub.groupby(
            ["merchant_surface", "bucket"],
            observed=True,
        )
        .size()
        .reset_index(name="count")
    )
    totals = grp.groupby(
        "merchant_surface", observed=True
    )["count"].transform("sum")
    grp["pct"] = (
        100.0 * grp["count"] / totals
    ).round(1)
    return grp


def territory_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Return comprehensive territory-level ATD performance metrics.

    Returns:
        DataFrame with columns ``territory``, ``mean_atd``,
        ``median_atd``, ``trip_count``, ``p25_atd``,
        ``p75_atd``, ``sla_rate`` (% trips within 45 min).
        Sorted ascending by ``median_atd``.
    """
    sub = df[["territory", "ATD"]].dropna().copy()
    if sub.empty:
        return pd.DataFrame(
            columns=[
                "territory", "mean_atd", "median_atd",
                "trip_count", "p25_atd", "p75_atd",
                "sla_rate",
            ]
        )
    grp = (
        sub.groupby("territory", observed=True)["ATD"]
        .agg(mean_atd="mean", median_atd="median",
             trip_count="count")
        .reset_index()
    )
    p25 = (
        sub.groupby("territory", observed=True)["ATD"]
        .quantile(0.25)
        .reset_index(name="p25_atd")
    )
    p75 = (
        sub.groupby("territory", observed=True)["ATD"]
        .quantile(0.75)
        .reset_index(name="p75_atd")
    )
    sub["within_sla"] = sub["ATD"] <= 45.0
    sla = (
        sub.groupby("territory", observed=True)["within_sla"]
        .mean()
        .mul(100)
        .round(1)
        .reset_index(name="sla_rate")
    )
    grp = (
        grp
        .merge(p25, on="territory")
        .merge(p75, on="territory")
        .merge(sla, on="territory")
        .sort_values("median_atd")
    )
    return grp


def geo_archetype_hour_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Return a geo_archetype × hour_local pivot of mean ATD.

    Returns:
        Pivot DataFrame indexed by ``geo_archetype`` with
        hour columns 0–23. Missing cells are NaN.
    """
    pivot = df.pivot_table(
        values="ATD",
        index="geo_archetype",
        columns="hour_local",
        aggfunc="mean",
    )
    return pivot.reindex(columns=_ALL_HOURS)


def sample_geo_archetype_atd(
    df: pd.DataFrame,
    n: int = 20_000,
) -> pd.DataFrame:
    """Return a random sample for geo_archetype ATD box plots.

    Args:
        df: Filtered DataFrame.
        n: Maximum number of rows to return.

    Returns:
        DataFrame with columns ``geo_archetype``, ``ATD``.
    """
    sub = df[["geo_archetype", "ATD"]].dropna()
    if len(sub) > n:
        sub = sub.sample(n=n, random_state=42)
    return sub.reset_index(drop=True)


def atd_pivot_courier_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Return a courier_flow × hour_local pivot of mean ATD.

    Args:
        df: Filtered DataFrame.

    Returns:
        DataFrame pivot with courier_flow rows and hour
        columns (0-23). Missing cells are NaN.
    """
    pivot = df.pivot_table(
        values="ATD",
        index="courier_flow",
        columns="hour_local",
        aggfunc="mean",
    )
    return pivot.reindex(columns=_ALL_HOURS)


def atd_daily_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """Return daily P25, P50, P75 ATD and trip count.

    Args:
        df: Filtered DataFrame with a ``date`` column.

    Returns:
        DataFrame with columns ``date``, ``p25``, ``p50``,
        ``p75``, ``trip_count``, sorted ascending by date.
    """
    sub = df[["date", "ATD"]].dropna()
    if sub.empty:
        return pd.DataFrame(
            columns=["date", "p25", "p50", "p75", "trip_count"]
        )
    grp = (
        sub.groupby("date")["ATD"]
        .agg(
            p25=lambda x: np.percentile(x, 25),
            p50=lambda x: np.percentile(x, 50),
            p75=lambda x: np.percentile(x, 75),
            trip_count="count",
        )
        .reset_index()
    )
    return grp.sort_values("date").reset_index(drop=True)


def sla_rate_by_distance_bins(
    df: pd.DataFrame,
    col: str,
    n_bins: int = 5,
    sla_min: float = 45.0,
) -> pd.DataFrame:
    """Return SLA pass rate per quantile bin of a distance column.

    Args:
        df: Filtered DataFrame.
        col: Distance column name (e.g. ``pickup_distance``).
        n_bins: Number of quantile bins.
        sla_min: SLA threshold in minutes.

    Returns:
        DataFrame with columns ``bin_label``, ``sla_rate``,
        ``mean_atd``, ``trip_count``.
    """
    sub = df[[col, "ATD"]].dropna().copy()
    if sub.empty:
        return pd.DataFrame(
            columns=[
                "bin_label", "sla_rate",
                "mean_atd", "trip_count",
            ]
        )
    sub["bin"] = pd.qcut(sub[col], q=n_bins, duplicates="drop")
    sub["within_sla"] = sub["ATD"] <= sla_min
    grp = (
        sub.groupby("bin", observed=True)
        .agg(
            mean_atd=("ATD", "mean"),
            trip_count=("ATD", "count"),
            sla_rate=(
                "within_sla",
                lambda x: round(100.0 * x.mean(), 1),
            ),
        )
        .reset_index()
    )
    grp["bin_label"] = grp["bin"].astype(str)
    return grp[["bin_label", "sla_rate", "mean_atd", "trip_count"]]


def scatter_pickup_dropoff_atd(
    df: pd.DataFrame,
    sample_size: int = 5000,
) -> pd.DataFrame:
    """Return a sample for a pickup vs dropoff distance scatter.

    Args:
        df: Filtered DataFrame.
        sample_size: Maximum rows to return.

    Returns:
        DataFrame with columns ``pickup_distance``,
        ``dropoff_distance``, ``ATD``.
    """
    cols = ["pickup_distance", "dropoff_distance", "ATD"]
    sub = df[cols].dropna()
    if len(sub) > sample_size:
        sub = sub.sample(n=sample_size, random_state=42)
    return sub.reset_index(drop=True)
