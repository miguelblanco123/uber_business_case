"""Step 13.2 · XGBoost on Top-N Features

Trains an XGBoost model restricted to the top N features by LightGBM
gain importance (from step 13). Saves model + metadata.
"""
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
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


def run(data_dir: Path, model_dir: Path, top_n: int = 15) -> dict:
    """Train XGBoost on the top-N LightGBM features.

    Args:
        data_dir:  Root data directory.
        model_dir: Directory where model artifacts are saved.
        top_n:     Number of top features (by LightGBM gain) to use.

    Returns:
        Dict with val metrics and output paths.
    """
    train_path    = data_dir / 'processed' / 'train.parquet'
    val_path      = data_dir / 'processed' / 'val.parquet'
    lgbm_model_p  = model_dir / 'lgbm_atd_model.pkl'
    lgbm_meta_p   = model_dir / 'model_metadata.json'
    model_path    = model_dir / f'xgb_top{top_n}_model.pkl'
    meta_path     = model_dir / f'xgb_top{top_n}_metadata.json'
    val_pred_path = (
        data_dir / 'processed' / 'val_predictions_xgb.parquet'
    )

    # ── Load ──────────────────────────────────────────────────────────────
    with open(lgbm_meta_p, 'r', encoding='utf-8') as fh:
        lgbm_meta = json.load(fh)

    target       = lgbm_meta['target']
    cat_features = lgbm_meta['cat_features']
    lgbm_model   = joblib.load(lgbm_model_p)

    df_train = pd.read_parquet(train_path)
    df_val   = pd.read_parquet(val_path)
    for col in cat_features:
        for split in [df_train, df_val]:
            if col in split.columns:
                split[col] = split[col].astype('category')

    y_train = df_train[target].values
    y_val   = df_val[target].values

    # ── Select top-N features ─────────────────────────────────────────────
    importance_df = pd.DataFrame({
        'feature': lgbm_model.feature_name(),
        'gain':    lgbm_model.feature_importance('gain'),
    }).sort_values('gain', ascending=False).reset_index(drop=True)

    top_features = importance_df.head(top_n)['feature'].tolist()
    top_cat      = [f for f in top_features if f in cat_features]

    logger.info(
        'Top-%s features selected (%s categorical): %s',
        top_n, len(top_cat),
        ', '.join(top_features),
    )

    # ── Build DMatrix ─────────────────────────────────────────────────────
    X_train = df_train[top_features].copy()
    X_val   = df_val[top_features].copy()
    for col in top_cat:
        X_val[col] = pd.Categorical(
            X_val[col],
            categories=X_train[col].cat.categories,
        )

    dtrain = xgb.DMatrix(
        X_train, label=y_train, enable_categorical=True
    )
    dval = xgb.DMatrix(
        X_val, label=y_val, enable_categorical=True
    )

    # ── Train ─────────────────────────────────────────────────────────────
    params = {
        'objective':        'reg:absoluteerror',
        'eval_metric':      ['mae', 'rmse'],
        'learning_rate':    0.05,
        'max_depth':        6,
        'min_child_weight': 50,
        'subsample':        0.8,
        'colsample_bytree': 0.8,
        'reg_alpha':        0.1,
        'reg_lambda':       0.1,
        'tree_method':      'hist',
        'seed':             SEED,
        'verbosity':        0,
    }

    logger.info(
        'Training XGBoost (reg:absoluteerror, top-%s features)...',
        top_n,
    )
    xgb_model = xgb.train(
        params,
        dtrain,
        num_boost_round=2000,
        evals=[(dtrain, 'train'), (dval, 'valid')],
        callbacks=[
            xgb.callback.EarlyStopping(rounds=50),
            xgb.callback.EvaluationMonitor(period=100),
        ],
    )
    logger.info(
        'Best iteration: %s  best val score: %.4f',
        xgb_model.best_iteration, xgb_model.best_score,
    )

    # ── Evaluate ──────────────────────────────────────────────────────────
    pred_val = np.clip(
        xgb_model.predict(
            dval,
            iteration_range=(0, xgb_model.best_iteration),
        ),
        a_min=0, a_max=None,
    )
    result   = _evaluate(y_val, pred_val, f'XGBoost top-{top_n}')
    mae_delta = result['MAE'] - lgbm_meta['val_mae']
    logger.info(
        'Val MAE=%.3f  RMSE=%.3f  R²=%.4f  '
        'delta vs LightGBM=%+.3f min (%+.1f%%)',
        result['MAE'], result['RMSE'], result['R2'],
        mae_delta,
        mae_delta / lgbm_meta['val_mae'] * 100,
    )
    logger.info(
        'Feature budget: %s / %s (%.0f%% of original set)',
        top_n, len(lgbm_meta['feature_cols']),
        top_n / len(lgbm_meta['feature_cols']) * 100,
    )

    # ── Save artifacts ────────────────────────────────────────────────────
    joblib.dump(xgb_model, model_path)
    logger.info('Model saved → %s', model_path)

    metadata = {
        'model':              'xgboost',
        'top_n':              top_n,
        'feature_cols':       top_features,
        'cat_features':       top_cat,
        'target':             target,
        'importance_source':  'lgbm_gain',
        'best_iteration':     int(xgb_model.best_iteration),
        'val_mae':            result['MAE'],
        'val_rmse':           result['RMSE'],
        'val_mape':           result['MAPE'],
        'val_r2':             result['R2'],
        'lgbm_val_mae':       lgbm_meta['val_mae'],
        'mae_delta_vs_lgbm':  round(mae_delta, 4),
        'sla_threshold_min':  SLA_THRESHOLD_MIN,
        'split_date_val_start':  lgbm_meta.get('split_date_val_start'),
        'split_date_test_start': lgbm_meta.get('split_date_test_start'),
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
        'mae_delta':  mae_delta,
        'model_path': model_path,
        'meta_path':  meta_path,
    }


if __name__ == '__main__':
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    parser = argparse.ArgumentParser(
        description='Train XGBoost on top-N LightGBM features.'
    )
    parser.add_argument(
        '--top-n', type=int, default=15,
        help='Number of top features to use (default: 15)',
    )
    args   = parser.parse_args()
    _root  = Path(__file__).parent.parent
    run(
        data_dir=_root / 'data',
        model_dir=_root / 'model',
        top_n=args.top_n,
    )
