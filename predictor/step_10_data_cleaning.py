"""Step 10 · Data Cleaning

Loads raw CSV, cleans ATD, imputes missing values, and writes
cleaned.parquet + preprocessed.parquet to data/processed/.
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ATD_MAX_MIN = 120
CRITICAL_COLS = [
    'ATD',
    'restaurant_offered_timestamp_utc',
    'eater_request_timestamp_local',
    'order_final_state_timestamp_local',
    'territory',
]
DASH_COLS = [
    'territory', 'country_name', 'workflow_uuid', 'driver_uuid',
    'delivery_trip_uuid', 'courier_flow',
    'restaurant_offered_timestamp_utc',
    'order_final_state_timestamp_local',
    'eater_request_timestamp_local',
    'geo_archetype', 'merchant_surface',
    'pickup_distance', 'dropoff_distance', 'ATD',
]


def run(data_dir: Path, model_dir: Path) -> dict:
    """Execute data cleaning pipeline.

    Args:
        data_dir:  Root data directory (contains raw/ and processed/).
        model_dir: Model directory (unused here, kept for API consistency).

    Returns:
        Dict with row counts and output paths.
    """
    raw_path   = data_dir / 'raw' / 'BC_A&A_with_ATD.csv'
    clean_path = data_dir / 'processed' / 'cleaned.parquet'
    prep_path  = data_dir / 'processed' / 'preprocessed.parquet'
    clean_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 1 · Load ──────────────────────────────────────────────────────────
    logger.info('Loading raw CSV from %s', raw_path)
    df = pd.read_csv(
        raw_path,
        dtype={
            'region':           'category',
            'territory':        'category',
            'country_name':     'category',
            'courier_flow':     'category',
            'geo_archetype':    'category',
            'merchant_surface': 'category',
        },
        parse_dates=[
            'restaurant_offered_timestamp_utc',
            'order_final_state_timestamp_local',
            'eater_request_timestamp_local',
        ],
        na_values=['\\N', 'NULL', 'None', ''],
    )
    logger.info('Loaded %s rows, %s columns', f'{len(df):,}', df.shape[1])

    # ── 2 · Remove invalid ATD rows ───────────────────────────────────────
    n0 = len(df)
    df = df[(df['ATD'] > 0) & (df['ATD'] <= ATD_MAX_MIN)].copy()
    logger.info(
        'ATD filter: removed %s rows → %s remaining',
        f'{n0 - len(df):,}', f'{len(df):,}',
    )

    # ── 3 · Drop rows missing critical columns ────────────────────────────
    n0 = len(df)
    df.dropna(subset=CRITICAL_COLS, inplace=True)
    logger.info(
        'Critical-null drop: removed %s rows → %s remaining',
        f'{n0 - len(df):,}', f'{len(df):,}',
    )

    # ── 4 · Distance: flag + impute ───────────────────────────────────────
    df['is_distance_missing'] = df['pickup_distance'].isna().astype('int8')
    for col in ['pickup_distance', 'dropoff_distance']:
        ter_median = df.groupby(
            'territory', observed=True
        )[col].transform('median')
        df[col] = df[col].fillna(ter_median).fillna(df[col].median())
    logger.info(
        'Distance imputed: %s rows',
        f'{df["is_distance_missing"].sum():,}',
    )

    # ── 5 · driver_uuid: flag + fill ─────────────────────────────────────
    df['driver_uuid_missing'] = df['driver_uuid'].isna().astype('int8')
    df['driver_uuid'] = df['driver_uuid'].fillna('UNKNOWN')
    logger.info(
        'Unknown drivers: %s (%.2f%%)',
        f'{df["driver_uuid_missing"].sum():,}',
        df['driver_uuid_missing'].mean() * 100,
    )

    # ── 6 · Save ──────────────────────────────────────────────────────────
    df.to_parquet(clean_path, index=False, engine='pyarrow')
    logger.info(
        'cleaned.parquet → %s  (%.1f MB)',
        df.shape, clean_path.stat().st_size / 1024 ** 2,
    )

    save_cols = [c for c in DASH_COLS if c in df.columns]
    df[save_cols].to_parquet(prep_path, index=False, engine='pyarrow')
    logger.info(
        'preprocessed.parquet → %.1f MB',
        prep_path.stat().st_size / 1024 ** 2,
    )

    return {
        'rows':       len(df),
        'clean_path': clean_path,
        'prep_path':  prep_path,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
