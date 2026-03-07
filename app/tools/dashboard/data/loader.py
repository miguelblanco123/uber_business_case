"""Load and parse the preprocessed ATD parquet file."""
import os

import pandas as pd
import requests
import streamlit as st

from tools.dashboard.data.cleaner import clean_data


def _ensure_parquet(path: str) -> None:
    """Download the parquet from Blob Storage if not present locally.

    Reads the SAS URL from the ``BLOB_SAS_URL`` environment variable.
    Raises ``RuntimeError`` if the variable is not set or the download
    fails.

    Args:
        path: Local filesystem path where the file should exist.
    """
    if os.path.exists(path):
        return

    sas_url = os.environ.get("BLOB_SAS_URL")
    if not sas_url:
        raise RuntimeError(
            "Parquet file not found locally and BLOB_SAS_URL "
            "environment variable is not set."
        )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    response = requests.get(sas_url, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download parquet from Blob Storage "
            f"(HTTP {response.status_code})."
        )

    with open(path, "wb") as fh:
        fh.write(response.content)

_BASE_COLS = [
    "territory",
    "country_name",
    "workflow_uuid",
    "driver_uuid",
    "delivery_trip_uuid",
    "courier_flow",
    "restaurant_offered_timestamp_utc",
    "order_final_state_timestamp_local",
    "eater_request_timestamp_local",
    "geo_archetype",
    "merchant_surface",
    "pickup_distance",
    "dropoff_distance",
    "ATD",
]

_DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Read parquet at *path*, clean, and derive helper columns.

    If the file is absent locally it is downloaded from Azure Blob
    Storage using the URL in the ``BLOB_SAS_URL`` environment variable.

    Returns a DataFrame with the 14 base columns plus:
    - ``hour_local``: local hour (0-23)
    - ``day_of_week``: integer 0=Mon
    - ``day_name``: string day name
    - ``date``: Python date object
    - ``total_distance``: pickup + dropoff distance (km)
    """
    _ensure_parquet(path)
    df = pd.read_parquet(path, columns=_BASE_COLS)
    df = clean_data(df)

    local_col = "eater_request_timestamp_local"
    if not pd.api.types.is_datetime64_any_dtype(df[local_col]):
        df[local_col] = pd.to_datetime(df[local_col])

    if "hour_local" not in df.columns:
        df["hour_local"] = df[local_col].dt.hour

    if "day_of_week" not in df.columns:
        df["day_of_week"] = df[local_col].dt.dayofweek

    if "day_name" not in df.columns:
        df["day_name"] = pd.Categorical(
            df[local_col].dt.day_name(),
            categories=_DAY_ORDER,
            ordered=True,
        )

    if "date" not in df.columns:
        df["date"] = df[local_col].dt.date

    if "total_distance" not in df.columns:
        df["total_distance"] = (
            df["pickup_distance"] + df["dropoff_distance"]
        )

    return df
