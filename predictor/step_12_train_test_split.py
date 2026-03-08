"""Step 12 · Train / Validation / Test Split

Time-based split + leakage-safe target re-encoding.
Writes train.parquet, val.parquet, test.parquet and updates
feature_manifest.json.
"""
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

HOLDOUT_DAYS = 14
VAL_DAYS     = 14


def run(data_dir: Path, model_dir: Path) -> dict:
    """Execute train/val/test split pipeline.

    Args:
        data_dir:  Root data directory.
        model_dir: Model directory (unused here).

    Returns:
        Dict with split sizes and output paths.
    """
    feat_path     = data_dir / 'processed' / 'features.parquet'
    manifest_path = data_dir / 'processed' / 'feature_manifest.json'
    train_path    = data_dir / 'processed' / 'train.parquet'
    val_path      = data_dir / 'processed' / 'val.parquet'
    test_path     = data_dir / 'processed' / 'test.parquet'

    with open(manifest_path, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    logger.info('Loading features from %s', feat_path)
    df = pd.read_parquet(feat_path)
    df['restaurant_offered_timestamp_utc'] = pd.to_datetime(
        df['restaurant_offered_timestamp_utc']
    )
    df = df.sort_values(
        'restaurant_offered_timestamp_utc'
    ).reset_index(drop=True)

    # ── Split boundaries ──────────────────────────────────────────────────
    ts         = df['restaurant_offered_timestamp_utc']
    max_date   = ts.max()
    test_start = max_date - pd.Timedelta(days=HOLDOUT_DAYS)
    val_start  = test_start - pd.Timedelta(days=VAL_DAYS)

    train_mask = ts < val_start
    val_mask   = (ts >= val_start) & (ts < test_start)
    test_mask  = ts >= test_start

    df_train = df[train_mask].copy()
    df_val   = df[val_mask].copy()
    df_test  = df[test_mask].copy()

    logger.info(
        'Split: train=%s  val=%s  test=%s',
        f'{len(df_train):,}', f'{len(df_val):,}', f'{len(df_test):,}',
    )
    logger.info(
        'Dates: val_start=%s  test_start=%s  end=%s',
        val_start.date(), test_start.date(), max_date.date(),
    )

    # ── Assert zero overlap ───────────────────────────────────────────────
    train_ts = set(df_train['restaurant_offered_timestamp_utc'].astype(str))
    val_ts   = set(df_val['restaurant_offered_timestamp_utc'].astype(str))
    test_ts  = set(df_test['restaurant_offered_timestamp_utc'].astype(str))
    assert not (train_ts & val_ts),  'Train/Val timestamp overlap!'
    assert not (val_ts & test_ts),   'Val/Test timestamp overlap!'
    assert not (train_ts & test_ts), 'Train/Test timestamp overlap!'

    # ── Fix target-encoding leakage ───────────────────────────────────────
    train_global_median = df_train['ATD'].median()

    territory_map = (
        df_train.groupby('territory', observed=True)['ATD'].median()
    )
    for split in [df_train, df_val, df_test]:
        split['territory_median_atd'] = (
            split['territory']
            .map(territory_map)
            .astype(float)
            .fillna(train_global_median)
        )

    geo_map = (
        df_train.groupby('geo_archetype', observed=True)['ATD'].median()
    )
    for split in [df_train, df_val, df_test]:
        split['geo_archetype_median_atd'] = (
            split['geo_archetype']
            .map(geo_map)
            .astype(float)
            .fillna(train_global_median)
        )

    if 'territory_flow_median_atd' in df_train.columns:
        flow_map = (
            df_train.groupby(
                ['territory', 'courier_flow'], observed=True
            )['ATD']
            .median()
        )
        for split in [df_train, df_val, df_test]:
            split['territory_flow_median_atd'] = (
                split.set_index(['territory', 'courier_flow'])
                .index.map(flow_map)
                .astype(float)
            )
            split['territory_flow_median_atd'] = (
                split['territory_flow_median_atd']
                .fillna(train_global_median)
            )

    if 'territory_hour_median_atd' in df_train.columns:
        hour_map = (
            df_train.groupby(
                ['territory', 'hour_local'], observed=True
            )['ATD']
            .median()
        )
        for split in [df_train, df_val, df_test]:
            split['territory_hour_median_atd'] = (
                split.set_index(['territory', 'hour_local'])
                .index.map(hour_map)
                .astype(float)
            )
            split['territory_hour_median_atd'] = (
                split['territory_hour_median_atd']
                .fillna(train_global_median)
            )

    logger.info(
        'Leakage fix applied. Train global ATD median: %.2f min',
        train_global_median,
    )

    # ── Save parquets ─────────────────────────────────────────────────────
    df_train.to_parquet(train_path, index=False, engine='pyarrow')
    df_val.to_parquet(val_path,     index=False, engine='pyarrow')
    df_test.to_parquet(test_path,   index=False, engine='pyarrow')
    logger.info(
        'Saved: train=%.1f MB  val=%.1f MB  test=%.1f MB',
        train_path.stat().st_size / 1024 ** 2,
        val_path.stat().st_size / 1024 ** 2,
        test_path.stat().st_size / 1024 ** 2,
    )

    # ── Update manifest ───────────────────────────────────────────────────
    manifest['split_date_val_start']  = str(val_start.date())
    manifest['split_date_test_start'] = str(test_start.date())
    manifest['split_date_end']        = str(max_date.date())
    with open(manifest_path, 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    return {
        'n_train':    len(df_train),
        'n_val':      len(df_val),
        'n_test':     len(df_test),
        'train_path': train_path,
        'val_path':   val_path,
        'test_path':  test_path,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
