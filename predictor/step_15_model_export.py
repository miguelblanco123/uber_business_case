"""Step 15 · Model Export

Sanity-checks the saved model, scores the full feature dataset, and
writes scored_dataset.parquet for the Streamlit dashboard.
"""
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_COLS = [
    'workflow_uuid',
    'driver_uuid',
    'delivery_trip_uuid',
    'restaurant_offered_timestamp_utc',
    'territory',
    'courier_flow',
    'geo_archetype',
    'merchant_surface',
    'ATD',
    'ATD_predicted',
    'hour_local',
    'is_peak_hour',
]


def run(data_dir: Path, model_dir: Path) -> dict:
    """Score the full dataset and save scored_dataset.parquet.

    Args:
        data_dir:  Root data directory.
        model_dir: Directory containing lgbm_atd_model.pkl.

    Returns:
        Dict with output path and row count.
    """
    feat_path   = data_dir / 'processed' / 'features.parquet'
    model_path  = model_dir / 'lgbm_atd_model.pkl'
    meta_path   = model_dir / 'model_metadata.json'
    scored_path = data_dir / 'processed' / 'scored_dataset.parquet'

    with open(meta_path, 'r', encoding='utf-8') as fh:
        meta = json.load(fh)

    model        = joblib.load(model_path)
    feature_cols = meta['feature_cols']
    cat_features = meta['cat_features']
    target       = meta['target']

    logger.info(
        'Model loaded: best_iter=%s  val_mae=%.3f',
        meta['best_iteration'], meta['val_mae'],
    )

    # ── Load full feature dataset ─────────────────────────────────────────
    logger.info('Loading full features from %s', feat_path)
    df_full = pd.read_parquet(feat_path)
    df_full['restaurant_offered_timestamp_utc'] = pd.to_datetime(
        df_full['restaurant_offered_timestamp_utc']
    )
    for col in cat_features:
        if col in df_full.columns:
            df_full[col] = df_full[col].astype('category')

    # ── Sanity check: 5-row prediction ───────────────────────────────────
    sanity_rows = df_full.head(5)
    X_sanity    = sanity_rows[
        [c for c in feature_cols if c in sanity_rows.columns]
    ]
    pred_sanity = np.clip(
        model.predict(X_sanity, num_iteration=meta['best_iteration']),
        a_min=0, a_max=None,
    )
    assert all(pred_sanity >= 0), 'Negative predictions — artifact corrupt!'
    logger.info(
        'Sanity check passed. Sample preds: %s',
        pred_sanity.round(2).tolist(),
    )

    # ── Score full dataset ────────────────────────────────────────────────
    X_full = df_full[
        [c for c in feature_cols if c in df_full.columns]
    ]
    logger.info('Scoring %s rows...', f'{len(df_full):,}')
    df_full['ATD_predicted'] = np.clip(
        model.predict(X_full, num_iteration=meta['best_iteration']),
        a_min=0, a_max=None,
    )
    logger.info(
        'ATD_predicted — mean=%.1f  median=%.1f  p90=%.1f',
        df_full['ATD_predicted'].mean(),
        df_full['ATD_predicted'].median(),
        df_full['ATD_predicted'].quantile(0.9),
    )

    # ── Save ──────────────────────────────────────────────────────────────
    save_cols  = [c for c in OUTPUT_COLS if c in df_full.columns]
    missing    = [c for c in OUTPUT_COLS if c not in df_full.columns]
    if missing:
        logger.warning('Columns missing from scored output: %s', missing)

    df_scored = df_full[save_cols].copy()
    for col in cat_features:
        if col in df_scored.columns:
            df_scored[col] = df_scored[col].astype(str)

    df_scored.to_parquet(scored_path, index=False, engine='pyarrow')
    size_mb = scored_path.stat().st_size / 1024 ** 2
    logger.info(
        'scored_dataset.parquet → %s  %s  %.1f MB',
        scored_path, df_scored.shape, size_mb,
    )

    sla_rate = float(
        np.mean(df_full['ATD_predicted'] <= meta['sla_threshold_min'])
        * 100
    )
    logger.info(
        'Export summary — val_mae=%.3f  sla_rate=%.1f%%  rows=%s',
        meta['val_mae'], sla_rate, f'{len(df_scored):,}',
    )

    return {
        'scored_path': scored_path,
        'n_rows':      len(df_scored),
        'sla_rate':    sla_rate,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
