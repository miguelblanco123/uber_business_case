"""Step 14 · Model Evaluation

Deep test-set evaluation: metrics, segment diagnostics, optional SHAP,
calibration check. Saves test_predictions.parquet.
"""
import json
import logging
from pathlib import Path

import joblib
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


def _segment_diagnostics(
    df_eval: pd.DataFrame,
    segment_cols: list[str],
) -> None:
    """Log MAE and median residual per segment group."""
    for seg in segment_cols:
        if seg not in df_eval.columns:
            continue
        tbl = (
            df_eval.groupby(seg, observed=True)
            .agg(
                n=('abs_error', 'count'),
                mae=('abs_error', 'mean'),
                median_residual=('residual', 'median'),
            )
            .round(2)
            .sort_values('mae', ascending=False)
        )
        logger.info('MAE by %s:\n%s', seg, tbl.to_string())


def _calibration_check(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> None:
    """Log mean predicted vs mean actual ATD by decile."""
    df_cal = pd.DataFrame({
        'actual':    y_true,
        'predicted': y_pred,
    })
    df_cal['decile'] = pd.qcut(
        df_cal['predicted'], q=10, labels=False, duplicates='drop'
    )
    summary = (
        df_cal.groupby('decile')[['actual', 'predicted']]
        .mean()
        .round(2)
    )
    logger.info('Calibration (mean by predicted decile):\n%s',
                summary.to_string())


def run(data_dir: Path, model_dir: Path) -> dict:
    """Evaluate LightGBM on the held-out test set.

    Args:
        data_dir:  Root data directory.
        model_dir: Directory containing lgbm_atd_model.pkl.

    Returns:
        Dict with test metrics and output path.
    """
    test_path      = data_dir / 'processed' / 'test.parquet'
    model_path     = model_dir / 'lgbm_atd_model.pkl'
    meta_path      = model_dir / 'model_metadata.json'
    test_pred_path = data_dir / 'processed' / 'test_predictions.parquet'

    with open(meta_path, 'r', encoding='utf-8') as fh:
        meta = json.load(fh)

    model        = joblib.load(model_path)
    feature_cols = meta['feature_cols']
    cat_features = meta['cat_features']
    target       = meta['target']

    df_test = pd.read_parquet(test_path)
    for col in cat_features:
        if col in df_test.columns:
            df_test[col] = df_test[col].astype('category')

    X_test = df_test[
        [c for c in feature_cols if c in df_test.columns]
    ]
    y_test = df_test[target].values

    logger.info(
        'Test rows=%s  features=%s',
        f'{len(df_test):,}', X_test.shape[1],
    )

    # ── Predict ───────────────────────────────────────────────────────────
    pred_test = np.clip(
        model.predict(X_test, num_iteration=meta['best_iteration']),
        a_min=0, a_max=None,
    )
    residuals = pred_test - y_test

    result = _evaluate(y_test, pred_test, 'LightGBM — Test')
    delta_mae = result['MAE'] - meta['val_mae']
    logger.info(
        'Test MAE=%.3f  RMSE=%.3f  MAPE=%.2f%%  R²=%.4f  '
        'delta vs val=%+.3f min (%s)',
        result['MAE'], result['RMSE'], result['MAPE'], result['R2'],
        delta_mae,
        'overfit signal' if delta_mae > 1 else 'no overfit',
    )
    logger.info(
        'Residuals — mean=%.3f  std=%.3f  '
        'within±5min=%.1f%%  within±10min=%.1f%%',
        residuals.mean(), residuals.std(),
        (np.abs(residuals) <= 5).mean() * 100,
        (np.abs(residuals) <= 10).mean() * 100,
    )

    # ── Segment diagnostics ───────────────────────────────────────────────
    df_eval = df_test.copy()
    df_eval['ATD_predicted'] = pred_test
    df_eval['residual']      = residuals
    df_eval['abs_error']     = np.abs(residuals)
    _segment_diagnostics(
        df_eval,
        ['territory', 'courier_flow', 'time_block',
         'geo_archetype', 'is_long_trip'],
    )

    # ── Calibration ───────────────────────────────────────────────────────
    _calibration_check(y_test, pred_test)

    # ── SHAP (optional) ───────────────────────────────────────────────────
    try:
        import shap
        rng        = np.random.default_rng(SEED)
        sample_idx = rng.choice(
            len(X_test), size=min(5000, len(X_test)), replace=False
        )
        X_shap      = X_test.iloc[sample_idx]
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_shap)
        shap_imp = pd.DataFrame({
            'feature':       X_shap.columns,
            'mean_abs_shap': np.abs(shap_values).mean(axis=0),
        }).sort_values('mean_abs_shap', ascending=False)
        logger.info(
            'Top-10 features by mean |SHAP|:\n%s',
            shap_imp.head(10).to_string(index=False),
        )
    except ImportError:
        logger.warning(
            'shap not installed — skipping SHAP analysis.'
            '  Install with: pip install shap'
        )

    # ── Save ──────────────────────────────────────────────────────────────
    test_preds_df = pd.DataFrame({
        'workflow_uuid': df_test['workflow_uuid'].values,
        'ATD':           y_test,
        'ATD_predicted': pred_test,
        'residual':      residuals,
    })
    test_preds_df.to_parquet(
        test_pred_path, index=False, engine='pyarrow'
    )
    logger.info(
        'Test predictions → %s  (%s rows)',
        test_pred_path, f'{len(test_preds_df):,}',
    )

    return {
        'test_mae':       result['MAE'],
        'test_rmse':      result['RMSE'],
        'test_r2':        result['R2'],
        'test_pred_path': test_pred_path,
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    _root = Path(__file__).parent.parent
    run(data_dir=_root / 'data', model_dir=_root / 'model')
