"""Predictor service layer — pure inference, zero Streamlit imports."""
import numpy as np
import pandas as pd
import xgboost as xgb

SLA_THRESHOLD_MIN = 45


def run_inference(
    df_rows: pd.DataFrame,
    model,
    meta: dict,
) -> pd.DataFrame:
    """Run XGBoost inference on the given rows.

    Args:
        df_rows:  DataFrame slice containing all required feature cols.
        model:    Loaded XGBoost booster.
        meta:     Model metadata dict (feature_cols, cat_features,
                  best_iteration).

    Returns:
        DataFrame with columns:
          predicted_atd, actual_atd, abs_error,
          sla_pred, sla_actual.
    """
    # Use model.feature_names as the authoritative feature list —
    # avoids mismatches when model and metadata are from different runs.
    feature_cols = model.feature_names
    cat_features = meta.get("cat_features", [])
    best_iter    = meta["best_iteration"]

    X = df_rows[
        [c for c in feature_cols if c in df_rows.columns]
    ].copy()

    for col in cat_features:
        if col in X.columns:
            X[col] = X[col].astype("category")

    dmatrix = xgb.DMatrix(X, enable_categorical=True)
    preds = np.clip(
        model.predict(dmatrix, iteration_range=(0, best_iter)),
        a_min=0,
        a_max=None,
    )

    actual = (
        df_rows["ATD"].values
        if "ATD" in df_rows.columns
        else np.full(len(preds), np.nan)
    )

    return pd.DataFrame(
        {
            "predicted_atd": preds.round(1),
            "actual_atd":    np.round(actual, 1),
            "abs_error":     np.round(np.abs(preds - actual), 1),
            "sla_pred":      preds <= SLA_THRESHOLD_MIN,
            "sla_actual":    actual <= SLA_THRESHOLD_MIN,
        },
        index=df_rows.index,
    )
