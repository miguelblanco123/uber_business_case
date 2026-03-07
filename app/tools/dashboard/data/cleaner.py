"""Clean raw ATD data: sentinels, nulls, invalid ATD, outliers."""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLS = [
    "ATD",
    "delivery_trip_uuid",
    "driver_uuid",
    "restaurant_offered_timestamp_utc",
]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of *df*.

    Steps:
    1. Replace ``\\N`` sentinel with NaN across all columns.
    2. Drop rows with NaN in critical columns.
    3. Remove rows with ATD <= 0.
    4. Remove ATD outliers via Tukey 3×IQR extreme fence
       (hard floor at 120 min).
    """
    n_start = len(df)

    # 1. Replace \\N
    df = df.replace(r"\\N", np.nan, regex=True)

    # 2. Drop rows missing critical columns
    df = df.dropna(subset=_REQUIRED_COLS)

    # 3. Remove non-positive ATD
    df = df[df["ATD"] > 0]

    # 4. Tukey 3×IQR extreme fence
    q1 = df["ATD"].quantile(0.25)
    q3 = df["ATD"].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 3 * iqr
    threshold = max(upper_fence, 120.0)
    df = df[df["ATD"] <= threshold]

    n_clean = len(df)
    n_removed = n_start - n_clean
    pct = 100.0 * n_removed / n_start if n_start > 0 else 0.0
    logger.info(
        "clean_data: removed %d rows (%.1f%%)."
        " ATD threshold: %.1f min. Remaining: %s",
        n_removed,
        pct,
        threshold,
        f"{n_clean:,}",
    )
    return df
