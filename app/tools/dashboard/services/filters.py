"""Apply sidebar filter selections to the ATD DataFrame."""
import pandas as pd


def apply_filters(
    df: pd.DataFrame,
    territories: list,
    courier_flows: list,
    geo_archetypes: list,
    atd_min: float,
    atd_max: float,
) -> pd.DataFrame:
    """Return rows of *df* matching all filter criteria.

    Each list filter uses AND logic; an empty list for any dimension
    returns an empty DataFrame (not all rows).

    Args:
        df: Full cleaned DataFrame.
        territories: Allowed territory values.
        courier_flows: Allowed courier_flow values.
        geo_archetypes: Allowed geo_archetype values.
        atd_min: Minimum ATD (inclusive).
        atd_max: Maximum ATD (inclusive).

    Returns:
        Filtered DataFrame (may be empty).
    """
    if not territories or not courier_flows or not geo_archetypes:
        return df.iloc[0:0]  # empty with same schema

    mask = (
        df["territory"].isin(territories)
        & df["courier_flow"].isin(courier_flows)
        & df["geo_archetype"].isin(geo_archetypes)
        & (df["ATD"] >= atd_min)
        & (df["ATD"] <= atd_max)
    )
    return df[mask]
