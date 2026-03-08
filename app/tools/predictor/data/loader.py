"""Predictor data layer — loads model artifacts and val sample."""
import json
import os
from pathlib import Path  # used for _ROOT / path construction

import joblib
import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = Path(os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..")))


VAL_PATH   = _ROOT / "data" / "processed" / "val.parquet"
MODEL_PATH = _ROOT / "model" / "minmax_scaler.pkl"
META_PATH  = _ROOT / "model" / "model_metadata.json"

_DISPLAY_COLS = [
    "territory",
    "courier_flow",
    "geo_archetype",
    "merchant_surface",
    "time_block",
    "hour_local",
    "pickup_distance",
    "dropoff_distance",
]

N_SAMPLE = 50
SEED     = 42


@st.cache_resource
def load_model():
    """Load and cache the XGBoost model artifact."""
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_meta(path: str = str(META_PATH)) -> dict:
    """Load and cache model metadata (feature list, best iteration).

    Args:
        path: Explicit path string — included in the cache key so
              changing META_PATH invalidates the cached result.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def load_val_sample() -> pd.DataFrame:
    """Return a reproducible 50-row sample from the validation set.

    Columns are limited to those useful for display + all feature
    columns needed for inference. ATD (actual) is retained but hidden
    from the selection table until after prediction.
    """
    df = pd.read_parquet(VAL_PATH)
    sample = (
        df.sample(n=min(N_SAMPLE, len(df)), random_state=SEED)
        .reset_index(drop=True)
    )
    # Round distances for readability
    for col in ("pickup_distance", "dropoff_distance"):
        if col in sample.columns:
            sample[col] = sample[col].round(2)
    return sample


def display_cols(df: pd.DataFrame) -> list[str]:
    """Return the subset of display columns present in df."""
    return [c for c in _DISPLAY_COLS if c in df.columns]
