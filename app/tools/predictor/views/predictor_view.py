"""Predictor view — ATD prediction on validation sample rows."""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.predictor.data.loader import (
    META_PATH,
    display_cols,
    load_meta,
    load_model,
    load_val_sample,
)
from tools.predictor.services.predict import (
    SLA_THRESHOLD_MIN,
    run_inference,
)

_GREEN  = "#06C167"
_RED    = "#FF4B4B"
_GOLD   = "#FFD700"
_BLACK  = "#000000"
_WHITE  = "#FFFFFF"


def _sla_badge(met: bool) -> str:
    color = _GREEN if met else _RED
    label = "Within SLA" if met else "Over SLA"
    return (
        f'<span style="background:{color};color:{_BLACK};'
        f'padding:2px 8px;border-radius:4px;font-size:0.8rem;">'
        f"{label}</span>"
    )


def _gauge(value: float, title: str, actual: float) -> go.Figure:
    """Donut-style gauge for a single ATD prediction."""
    pct = min(value / 120, 1.0)
    color = _GREEN if value <= SLA_THRESHOLD_MIN else _RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={
            "reference": actual,
            "valueformat": ".1f",
            "suffix": " min",
            "increasing": {"color": _RED},
            "decreasing": {"color": _GREEN},
        },
        number={"suffix": " min", "font": {"size": 36}},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {
                "range": [0, 120],
                "tickcolor": _BLACK,
            },
            "bar": {"color": color},
            "bgcolor": _WHITE,
            "borderwidth": 1,
            "bordercolor": "#cccccc",
            "steps": [
                {"range": [0, SLA_THRESHOLD_MIN],
                 "color": "#e6f9f0"},
                {"range": [SLA_THRESHOLD_MIN, 120],
                 "color": "#fde8e8"},
            ],
            "threshold": {
                "line": {"color": _GOLD, "width": 3},
                "thickness": 0.75,
                "value": actual,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=40, b=10, l=20, r=20),
        paper_bgcolor=_WHITE,
        font_color=_BLACK,
    )
    return fig


def _comparison_bar(results: pd.DataFrame, sample: pd.DataFrame) -> go.Figure:
    """Grouped bar chart: predicted vs actual ATD for selected rows."""
    labels = [
        f"Row {i} · {sample.loc[i, 'territory']}"
        if "territory" in sample.columns else f"Row {i}"
        for i in results.index
    ]
    fig = go.Figure()
    fig.add_bar(
        name="Predicted",
        x=labels,
        y=results["predicted_atd"],
        marker_color=_GREEN,
    )
    fig.add_bar(
        name="Actual",
        x=labels,
        y=results["actual_atd"],
        marker_color="#888888",
    )
    fig.add_hline(
        y=SLA_THRESHOLD_MIN,
        line_dash="dash",
        line_color=_GOLD,
        annotation_text=f"SLA {SLA_THRESHOLD_MIN} min",
        annotation_position="top right",
    )
    fig.update_layout(
        barmode="group",
        plot_bgcolor=_WHITE,
        paper_bgcolor=_WHITE,
        font_color=_BLACK,
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=40, b=40, l=40, r=20),
        yaxis_title="ATD (min)",
        height=320,
    )
    return fig


def _render_model_metrics(meta: dict) -> None:
    """Render a compact model performance banner."""
    st.subheader("Model Performance")

    mae_delta = meta.get("mae_delta_vs_lgbm", 0)
    delta_pct = (
        mae_delta / meta.get("lgbm_val_mae", 1) * 100
        if meta.get("lgbm_val_mae") else 0
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Val MAE", f"{meta['val_mae']:.2f} min",
              help="Mean Absolute Error on the held-out validation set")
    c2.metric("Val RMSE", f"{meta['val_rmse']:.2f} min",
              help="Root Mean Squared Error — penalises large errors")
    c3.metric("Val R²", f"{meta['val_r2']:.3f}",
              help="Fraction of ATD variance explained by the model")

    with st.expander(
        f"Model details — XGBoost · top 25 features "
        f"· {meta['best_iteration']} trees"
    ):
        left, right = st.columns(2)
        with left:
            st.markdown(
                f"**Algorithm** XGBoost (`reg:absoluteerror`)  \n"
                f"**Feature selection** top-25 "
                f"by LightGBM gain  \n"
                f"**Best iteration** {meta['best_iteration']}  \n"
                f"**Val split** {meta.get('split_date_val_start', '—')} "
                f"→ {meta.get('split_date_test_start', '—')}  \n"
                f"**SLA threshold** {meta.get('sla_threshold_min', 45)} min"
            )
        with right:
            features = meta.get("feature_cols", [])
            st.markdown(
                "**Features used**  \n"
                + "  \n".join(f"`{f}`" for f in features)
            )

    st.markdown("---")


def predictor_view() -> None:
    """Render the ATD predictor page."""
    st.title("ATD Predictor")
    st.caption(
        "Select one or more trips from the validation sample, "
        "then click **Run Prediction** to see the model's estimate."
    )

    # ── Load artifacts ────────────────────────────────────────────────────
    try:
        model  = load_model()
        meta   = load_meta(str(META_PATH))
        sample = load_val_sample()
    except FileNotFoundError as exc:
        st.error(
            f"Required file not found: `{exc.filename}`.  "
            "Run the retraining pipeline first:\n\n"
            "```\npython predictor/retrain.py\n```"
        )
        return

    _render_model_metrics(meta)

    # ── Row selection table ───────────────────────────────────────────────
    st.subheader("Validation Sample")
    st.caption(
        f"{len(sample)} rows drawn from the validation set "
        f"(Mar 31 – Apr 13 2025). Actual ATD revealed after prediction."
    )

    dcols      = display_cols(sample)
    display_df = sample[dcols].copy()

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=False,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "hour_local":       st.column_config.NumberColumn("Hour", format="%d:00"),
            "pickup_distance":  st.column_config.NumberColumn("Pickup (km)", format="%.2f"),
            "dropoff_distance": st.column_config.NumberColumn("Dropoff (km)", format="%.2f"),
        },
    )

    selected_rows = event.selection.get("rows", [])  # type: ignore[union-attr]

    if not selected_rows:
        st.info("Select one or more rows in the table above, then click **Run Prediction**.")
        return

    st.caption(f"{len(selected_rows)} row(s) selected.")

    # ── Predict ───────────────────────────────────────────────────────────
    if st.button("Run Prediction", type="primary"):
        selected_df = sample.iloc[selected_rows]
        results     = run_inference(selected_df, model, meta)

        st.markdown("---")
        st.subheader("Prediction Results")

        # Summary comparison chart (only when >1 row)
        if len(selected_rows) > 1:
            st.plotly_chart(
                _comparison_bar(results, sample),
                use_container_width=True,
            )

        # Per-row detail cards
        for idx, row_idx in enumerate(results.index):
            res  = results.loc[row_idx]
            info = sample.loc[row_idx]
            territory = info.get("territory", "—")
            flow      = info.get("courier_flow", "—")

            with st.container(border=True):
                header_cols = st.columns([3, 1])
                with header_cols[0]:
                    st.markdown(
                        f"**Row {row_idx}** · {territory} · {flow}"
                    )
                with header_cols[1]:
                    st.markdown(
                        _sla_badge(bool(res["sla_pred"])),
                        unsafe_allow_html=True,
                    )

                gauge_col, metric_col = st.columns([2, 1])
                with gauge_col:
                    st.plotly_chart(
                        _gauge(
                            float(res["predicted_atd"]),
                            "Predicted ATD",
                            float(res["actual_atd"]),
                        ),
                        use_container_width=True,
                        key=f"gauge_{row_idx}",
                    )
                with metric_col:
                    st.metric(
                        "Predicted ATD",
                        f"{res['predicted_atd']:.1f} min",
                    )
                    st.metric(
                        "Actual ATD",
                        f"{res['actual_atd']:.1f} min",
                        delta=f"{res['predicted_atd'] - res['actual_atd']:+.1f} min",
                        delta_color="inverse",
                    )
                    st.metric(
                        "Abs Error",
                        f"{res['abs_error']:.1f} min",
                    )
                    st.markdown(
                        f"Actual SLA: {_sla_badge(bool(res['sla_actual']))}",
                        unsafe_allow_html=True,
                    )

        # Summary table
        st.markdown("---")
        summary = results.copy()
        summary.index.name = "row"
        summary.columns = [
            "Predicted (min)", "Actual (min)",
            "Abs Error (min)", "SLA Pred", "SLA Actual",
        ]
        st.dataframe(summary, use_container_width=True)
