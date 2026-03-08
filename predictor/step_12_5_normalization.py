"""Step 12.5 · MinMax Normalization

Fits a MinMaxScaler on train numeric features only, transforms all
three splits in-place, and persists the scaler for inference.

Inputs  : data/processed/{train,val,test}.parquet
          data/processed/feature_manifest.json
Outputs : data/processed/{train,val,test}.parquet  (overwritten)
          model/minmax_scaler.pkl
"""
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

# Columns that must NOT be scaled
_EXCLUDE = {
    'ATD',                  # target — never scale
    'workflow_uuid',
    'driver_uuid',
    'delivery_trip_uuid',
    'restaurant_offered_timestamp_utc',
}


def _numeric_cols(df: pd.DataFrame, manifest: dict) -> list[str]:
    """Return numeric feature columns eligible for scaling.

    Excludes the target, ID columns, and any categorical columns
    (object / category dtype) that slipped through.
    """
    candidates = [
        c for c in manifest.get('numeric_features', [])
        if c in df.columns and c not in _EXCLUDE
    ]
    # Keep only columns with a true numeric dtype
    return [
        c for c in candidates
        if pd.api.types.is_numeric_dtype(df[c])
    ]


def run(data_dir: Path, model_dir: Path) -> dict:
    """Fit MinMaxScaler on train, transform all splits, save scaler.

    Args:
        data_dir:  Root data directory.
        model_dir: Directory where the scaler artifact is saved.

    Returns:
        Dict with scaler path and columns scaled.
    """
    train_path    = data_dir / 'processed' / 'train.parquet'
    val_path      = data_dir / 'processed' / 'val.parquet'
    test_path     = data_dir / 'processed' / 'test.parquet'
    manifest_path = data_dir / 'processed' / 'feature_manifest.json'
    scaler_path   = model_dir / 'minmax_scaler.pkl'
    model_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    df_train = pd.read_parquet(train_path)
    df_val   = pd.read_parquet(val_path)
    df_test  = pd.read_parquet(test_path)

    cols = _numeric_cols(df_train, manifest)
    logger.info('Scaling %s numeric columns.', len(cols))

    # Fit on train only — no leakage into val/test
    scaler = MinMaxScaler()
    df_train[cols] = scaler.fit_transform(df_train[cols])

    # Apply to val and test using train statistics
    df_val[cols]  = scaler.transform(df_val[cols])
    df_test[cols] = scaler.transform(df_test[cols])

    logger.info(
        'Feature ranges after scaling — '
        'train min=%.4f  max=%.4f',
        df_train[cols].min().min(),
        df_train[cols].max().max(),
    )

    # Overwrite parquets in-place
    df_train.to_parquet(train_path, index=False, engine='pyarrow')
    df_val.to_parquet(val_path,     index=False, engine='pyarrow')
    df_test.to_parquet(test_path,   index=False, engine='pyarrow')
    logger.info('Scaled parquets written.')

    joblib.dump(scaler, scaler_path)
    logger.info('Scaler saved → %s', scaler_path)

    # Persist metadata for auditability and inference pipelines
    scaler_meta = {
        'columns_scaled': cols,
        'n_cols':          len(cols),
        'feature_range':   list(scaler.feature_range),
        'data_min':        scaler.data_min_.tolist(),
        'data_max':        scaler.data_max_.tolist(),
        'data_range':      scaler.data_range_.tolist(),
        'n_train_rows':    len(df_train),
    }
    meta_path = model_dir / 'minmax_scaler_metadata.json'
    with open(meta_path, 'w', encoding='utf-8') as fh:
        json.dump(scaler_meta, fh, indent=2)
    logger.info('Scaler metadata saved → %s', meta_path)

    return {
        'scaler_path':    scaler_path,
        'meta_path':      meta_path,
        'columns_scaled': cols,
        'n_cols':         len(cols),
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
