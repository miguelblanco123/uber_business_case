"""Step 11 · Feature Engineering

Reads cleaned.parquet and produces features.parquet +
feature_manifest.json in data/processed/.
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

logger = logging.getLogger(__name__)

SLA_MIN          = 45
MIN_DRIVER_TRIPS = 5
TIME_BLOCK_ORDER = [
    'overnight', 'morning', 'lunch',
    'afternoon', 'dinner', 'late_night',
]
NUMERIC_FEATURES = [
    'hour_local', 'day_of_week', 'is_weekend', 'is_peak_hour',
    'week_number', 'month',
    'pickup_distance', 'dropoff_distance', 'total_distance',
    'distance_ratio', 'log_pickup', 'log_dropoff', 'log_total_dist',
    'is_long_trip', 'is_distance_missing',
    'driver_mean_atd', 'driver_median_atd', 'driver_p90_atd',
    'driver_std_atd', 'driver_sla_rate',
    'driver_trip_count', 'driver_log_trips', 'driver_is_new',
    'driver_mean_atd_30d', 'driver_trip_count_30d',
    'driver_sla_rate_30d',
    'driver_mean_atd_7d', 'driver_trip_count_7d',
    'driver_peak_hour_ratio', 'driver_weekend_ratio',
    'driver_territory_entropy',
    'territory_median_atd', 'geo_archetype_median_atd',
    'territory_flow_median_atd', 'territory_hour_median_atd',
    'territory_code', 'courier_flow_code',
    'geo_archetype_code', 'merchant_surface_code', 'time_block_code',
    'region_code', 'country_name_code',
]
CAT_FEATURES = [
    'territory', 'courier_flow',
    'geo_archetype', 'merchant_surface', 'time_block',
    'region', 'country_name',
]


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour, day, peak, block, and calendar features."""
    req = df['eater_request_timestamp_local']
    df['hour_local']  = req.dt.hour
    df['day_of_week'] = req.dt.dayofweek
    df['is_weekend']  = df['day_of_week'].isin([5, 6]).astype(int)
    df['week_number'] = req.dt.isocalendar().week.astype('Int32')
    df['month']       = req.dt.month
    df['is_peak_hour'] = df['hour_local'].isin(
        set(range(12, 15)) | set(range(19, 24))
    ).astype(int)

    h = df['hour_local']
    df['time_block'] = pd.Categorical(
        np.select(
            condlist=[
                (h >= 6)  & (h < 11),
                (h >= 11) & (h < 14),
                (h >= 14) & (h < 18),
                (h >= 18) & (h < 22),
                (h >= 22),
            ],
            choicelist=[
                'morning', 'lunch', 'afternoon', 'dinner', 'late_night',
            ],
            default='overnight',
        ),
        categories=TIME_BLOCK_ORDER,
        ordered=True,
    )
    return df


def _add_distance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived distance columns."""
    df['total_distance'] = (
        df['pickup_distance'] + df['dropoff_distance']
    )
    df['distance_ratio'] = (
        df['dropoff_distance'] / (df['pickup_distance'] + 0.001)
    )
    df['is_long_trip']   = (df['total_distance'] > 5).astype(int)
    df['log_pickup']     = np.log1p(df['pickup_distance'])
    df['log_dropoff']    = np.log1p(df['dropoff_distance'])
    df['log_total_dist'] = np.log1p(df['total_distance'])
    return df


def _add_driver_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add expanding/rolling driver aggregate features."""
    df = df.sort_values(
        'restaurant_offered_timestamp_utc'
    ).reset_index(drop=True)

    g = df.groupby('driver_uuid', sort=False)['ATD']

    df['driver_mean_atd']   = g.transform(
        lambda x: x.expanding().mean().shift(1)
    )
    df['driver_median_atd'] = g.transform(
        lambda x: x.expanding().median().shift(1)
    )
    df['driver_p90_atd']    = g.transform(
        lambda x: x.expanding().quantile(0.90).shift(1)
    )
    df['driver_std_atd']    = g.transform(
        lambda x: x.expanding().std().shift(1)
    ).fillna(0)
    df['driver_sla_rate']   = (
        df.groupby('driver_uuid', sort=False)['ATD']
        .transform(
            lambda x: (x <= SLA_MIN).expanding().mean().shift(1)
        )
    )
    df['driver_trip_count'] = g.transform(
        lambda x: x.expanding().count().shift(1)
    ).fillna(0).astype(int)
    df['driver_log_trips']  = np.log1p(df['driver_trip_count'])

    # Rolling windows
    df = df.set_index('restaurant_offered_timestamp_utc')
    for window, suffix in [('30D', '30d'), ('7D', '7d')]:
        df[f'driver_mean_atd_{suffix}'] = (
            df.groupby('driver_uuid', sort=False)['ATD']
            .transform(
                lambda x: x.rolling(window, closed='left').mean()
            )
        )
        df[f'driver_trip_count_{suffix}'] = (
            df.groupby('driver_uuid', sort=False)['ATD']
            .transform(
                lambda x: x.rolling(window, closed='left').count()
            )
        ).fillna(0).astype(int)

    df['driver_sla_rate_30d'] = (
        df.groupby('driver_uuid', sort=False)['ATD']
        .transform(
            lambda x: (
                (x <= SLA_MIN).rolling('30D', closed='left').mean()
            )
        )
    )
    df = df.reset_index()

    # Behavioural
    df['driver_peak_hour_ratio'] = (
        df.groupby('driver_uuid', sort=False)['is_peak_hour']
        .transform('mean')
    )
    df['driver_weekend_ratio'] = (
        df.groupby('driver_uuid', sort=False)['is_weekend']
        .transform('mean')
    )

    def _entropy(s: pd.Series) -> float:
        counts = s.value_counts(normalize=True)
        return float(scipy_entropy(counts))

    driver_entropy = (
        df[df['driver_uuid'] != 'UNKNOWN']
        .groupby('driver_uuid')['territory']
        .apply(_entropy)
    )
    df['driver_territory_entropy'] = (
        df['driver_uuid'].map(driver_entropy).fillna(0.0)
    )

    return df


def _apply_driver_guard(df: pd.DataFrame) -> pd.DataFrame:
    """Impute driver stats for drivers with < MIN_DRIVER_TRIPS trips."""
    driver_cols = [
        'driver_mean_atd', 'driver_median_atd', 'driver_p90_atd',
        'driver_std_atd', 'driver_sla_rate',
        'driver_mean_atd_30d', 'driver_sla_rate_30d',
        'driver_mean_atd_7d',
    ]
    new_mask = df['driver_trip_count'] < MIN_DRIVER_TRIPS
    df['driver_is_new'] = new_mask.astype('int8')
    for col in driver_cols:
        global_med = df.loc[~new_mask, col].median()
        df.loc[new_mask, col] = global_med
        df[col] = df[col].fillna(global_med)
    logger.info(
        'Driver guard: %s rows imputed (%.1f%%)',
        f'{new_mask.sum():,}', new_mask.mean() * 100,
    )
    return df


def _add_encodings(df: pd.DataFrame) -> pd.DataFrame:
    """Add category codes, target-encoded medians and interactions."""
    all_cats = [
        'territory', 'courier_flow', 'geo_archetype',
        'merchant_surface', 'time_block', 'region', 'country_name',
    ]
    for col in all_cats:
        if col not in df.columns:
            continue
        if df[col].dtype.name != 'category':
            df[col] = df[col].astype('category')
        df[f'{col}_code'] = df[col].cat.codes

    df['territory_median_atd'] = (
        df.groupby('territory', observed=True)['ATD']
        .transform('median')
    )
    df['geo_archetype_median_atd'] = (
        df.groupby('geo_archetype', observed=True)['ATD']
        .transform('median')
    )
    df['territory_flow_median_atd'] = (
        df.groupby(
            ['territory', 'courier_flow'], observed=True
        )['ATD']
        .transform('median')
    )
    df['territory_hour_median_atd'] = (
        df.groupby(
            ['territory', 'hour_local'], observed=True
        )['ATD']
        .transform('median')
    )
    return df


def _check_feature_ranges(df: pd.DataFrame) -> None:
    """Log min/max/null stats for numeric features; flag anomalies."""
    # Categorical columns can't use min/max without ordering — use codes
    num_cols = [c for c in NUMERIC_FEATURES if c in df.columns]
    stats = df[num_cols].agg(['min', 'max', 'mean', 'std', 'median']).T
    stats['null_count'] = df[num_cols].isna().sum()
    stats['null_%'] = (stats['null_count'] / len(df) * 100).round(2)
    stats['flag']   = ''
    stats.loc[stats['min'] < 0, 'flag']   += 'negative '
    stats.loc[stats['null_%'] > 5, 'flag'] += 'high_null '
    stats.loc[
        (stats['max'] - stats['min']) == 0, 'flag'
    ] += 'zero_variance '

    flagged = stats[stats['flag'].str.strip() != '']
    if flagged.empty:
        logger.info('Feature range check: no issues detected.')
    else:
        logger.warning(
            'Feature range check: %s flagged feature(s):\n%s',
            len(flagged),
            flagged[['min', 'max', 'null_%', 'flag']].to_string(),
        )


def run(data_dir: Path, model_dir: Path) -> dict:
    """Execute feature engineering pipeline.

    Args:
        data_dir:  Root data directory.
        model_dir: Model directory (unused here).

    Returns:
        Dict with output paths and feature lists.
    """
    clean_path    = data_dir / 'processed' / 'cleaned.parquet'
    feat_path     = data_dir / 'processed' / 'features.parquet'
    manifest_path = data_dir / 'processed' / 'feature_manifest.json'

    logger.info('Loading cleaned data from %s', clean_path)
    df = pd.read_parquet(clean_path)
    for col in [
        'restaurant_offered_timestamp_utc',
        'order_final_state_timestamp_local',
        'eater_request_timestamp_local',
    ]:
        df[col] = pd.to_datetime(df[col])

    logger.info('Adding time features...')
    df = _add_time_features(df)

    logger.info('Adding distance features...')
    df = _add_distance_features(df)

    logger.info('Adding driver aggregate features (slow)...')
    df = _add_driver_features(df)
    df = _apply_driver_guard(df)

    logger.info('Adding encodings...')
    df = _add_encodings(df)

    logger.info('Checking feature ranges...')
    _check_feature_ranges(df)

    # Save
    id_cols = [
        'workflow_uuid', 'driver_uuid', 'delivery_trip_uuid',
        'restaurant_offered_timestamp_utc',
    ]
    numeric_feats = [c for c in NUMERIC_FEATURES if c in df.columns]
    save_cols = (
        [c for c in id_cols if c in df.columns]
        + numeric_feats
        + [c for c in CAT_FEATURES if c in df.columns]
        + ['ATD']
    )
    df[save_cols].to_parquet(feat_path, index=False, engine='pyarrow')
    logger.info(
        'features.parquet → %s  (%.1f MB)',
        df[save_cols].shape,
        feat_path.stat().st_size / 1024 ** 2,
    )

    manifest = {
        'numeric_features': numeric_feats,
        'cat_features':     CAT_FEATURES,
        'target':           'ATD',
        'sla_threshold_min': SLA_MIN,
        'min_driver_trips':  MIN_DRIVER_TRIPS,
    }
    with open(manifest_path, 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)
    logger.info('feature_manifest.json saved.')

    return {
        'feat_path':     feat_path,
        'manifest_path': manifest_path,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
