"""Step 13 · LightGBM Model Training

Trains a LightGBM regression_l1 model on the train split, evaluates
on validation, and saves the model + metadata.
"""
import json
import logging
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

logger = logging.getLogger(__name__)

SEED              = 42
SLA_THRESHOLD_MIN = 45


def _compute_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Return MAPE excluding zero actuals."""
    mask = y_true > 0
    return float(
        np.mean(
            np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])
        ) * 100
    )


def _evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label: str = 'Model',
) -> dict:
    """Compute MAE, RMSE, MAPE, R² and SLA hit-rate."""
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = _compute_mape(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    sla  = float(np.mean(y_pred <= SLA_THRESHOLD_MIN) * 100)
    return {
        'label': label,
        'MAE':   round(mae, 3),
        'RMSE':  round(rmse, 3),
        'MAPE':  round(mape, 2),
        'R2':    round(r2, 4),
        'SLA_%': round(sla, 2),
    }


def run(data_dir: Path, model_dir: Path) -> dict:
    """Train LightGBM and persist artifacts.

    Args:
        data_dir:  Root data directory.
        model_dir: Directory where model artifacts are saved.

    Returns:
        Dict with val metrics and output paths.
    """
    train_path    = data_dir / 'processed' / 'train.parquet'
    val_path      = data_dir / 'processed' / 'val.parquet'
    manifest_path = data_dir / 'processed' / 'feature_manifest.json'
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path    = model_dir / 'lgbm_atd_model.pkl'
    meta_path     = model_dir / 'model_metadata.json'
    val_pred_path = data_dir / 'processed' / 'val_predictions.parquet'

    # ── Load data ─────────────────────────────────────────────────────────
    with open(manifest_path, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    numeric_features = manifest['numeric_features']
    cat_features     = manifest['cat_features']
    target           = manifest['target']

    df_train = pd.read_parquet(train_path)
    df_val   = pd.read_parquet(val_path)

    for col in cat_features:
        for split in [df_train, df_val]:
            if col in split.columns:
                split[col] = split[col].astype('category')

    feature_cols = [
        c for c in numeric_features + cat_features
        if c in df_train.columns
    ]
    y_train = df_train[target].values
    y_val   = df_val[target].values

    logger.info(
        'Train=%s  Val=%s  Features=%s',
        f'{len(df_train):,}', f'{len(df_val):,}', len(feature_cols),
    )

    # ── Baselines ─────────────────────────────────────────────────────────
    global_mean = y_train.mean()
    pred_mean   = np.full(len(y_val), global_mean)
    res_mean    = _evaluate(y_val, pred_mean, 'Baseline: Global Mean')

    seg_median = (
        df_train.groupby(
            ['territory', 'courier_flow'], observed=True
        )[target]
        .median()
        .reset_index()
        .rename(columns={target: 'seg_median'})
    )
    pred_seg = (
        df_val[['territory', 'courier_flow']]
        .merge(seg_median, on=['territory', 'courier_flow'], how='left')
        ['seg_median']
        .fillna(global_mean)
        .values
    )
    res_seg = _evaluate(
        y_val, pred_seg, 'Baseline: Territory×Flow Median'
    )
    logger.info(
        '%s  MAE=%.2f', res_mean['label'], res_mean['MAE']
    )
    logger.info(
        '%s  MAE=%.2f', res_seg['label'], res_seg['MAE']
    )

    # ── Align categories ──────────────────────────────────────────────────
    X_train = df_train[feature_cols]
    X_val   = df_val[feature_cols].copy()
    for col in cat_features:
        if col in X_train.columns:
            X_val[col] = pd.Categorical(
                X_val[col],
                categories=X_train[col].cat.categories,
            )

    lgb_train = lgb.Dataset(
        X_train, label=y_train,
        categorical_feature=cat_features,
        free_raw_data=False,
    )
    lgb_val = lgb.Dataset(
        X_val, label=y_val,
        categorical_feature=cat_features,
        reference=lgb_train,
        free_raw_data=False,
    )

    params = {
        'objective':        'regression_l1',
        'metric':           ['mae', 'rmse'],
        'learning_rate':    0.02,   # lowered: lets model train longer
        'num_leaves':       255,    # increased: more model capacity
        'min_data_in_leaf': 50,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq':     5,
        'reg_alpha':        0.1,
        'reg_lambda':       0.1,
        'verbose':          -1,
        'seed':             SEED,
    }

    callbacks = [
        lgb.early_stopping(stopping_rounds=100, verbose=False),
        lgb.log_evaluation(period=200),
    ]

    logger.info(
        'Training LightGBM (regression_l1, early stopping)...'
    )
    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=5000,
        valid_sets=[lgb_train, lgb_val],
        valid_names=['train', 'valid'],
        callbacks=callbacks,
    )
    logger.info('Best iteration: %s', model.best_iteration)

    # ── Evaluate ──────────────────────────────────────────────────────────
    pred_val = np.clip(
        model.predict(X_val, num_iteration=model.best_iteration),
        a_min=0, a_max=None,
    )
    result = _evaluate(y_val, pred_val, 'LightGBM')
    best_baseline_mae = min(res_mean['MAE'], res_seg['MAE'])
    improvement = (
        (best_baseline_mae - result['MAE']) / best_baseline_mae * 100
    )
    logger.info(
        'Val MAE=%.3f  RMSE=%.3f  MAPE=%.2f%%  R²=%.4f  '
        'improvement vs baseline=%.1f%%',
        result['MAE'], result['RMSE'], result['MAPE'],
        result['R2'], improvement,
    )

    # ── Save artifacts ────────────────────────────────────────────────────
    joblib.dump(model, model_path)
    logger.info('Model saved → %s', model_path)

    metadata = {
        'feature_cols':          feature_cols,
        'numeric_features':      numeric_features,
        'cat_features':          cat_features,
        'target':                target,
        'split_date_test_start': manifest.get('split_date_test_start'),
        'split_date_val_start':  manifest.get('split_date_val_start'),
        'best_iteration':        int(model.best_iteration),
        'val_mae':               result['MAE'],
        'val_rmse':              result['RMSE'],
        'val_mape':              result['MAPE'],
        'val_r2':                result['R2'],
        'sla_threshold_min':     SLA_THRESHOLD_MIN,
    }
    with open(meta_path, 'w', encoding='utf-8') as fh:
        json.dump(metadata, fh, indent=2)
    logger.info('Metadata saved → %s', meta_path)

    val_preds_df = pd.DataFrame({
        'workflow_uuid': df_val['workflow_uuid'].values,
        'ATD':           y_val,
        'ATD_predicted': pred_val,
    })
    val_preds_df.to_parquet(val_pred_path, index=False, engine='pyarrow')
    logger.info(
        'Val predictions → %s  (%s rows)',
        val_pred_path, f'{len(val_preds_df):,}',
    )

    return {
        'val_mae':    result['MAE'],
        'val_rmse':   result['RMSE'],
        'val_r2':     result['R2'],
        'model_path': model_path,
        'meta_path':  meta_path,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
