"""Tab 3 — Courier & Platform: flow and merchant surface charts."""
import pandas as pd
import plotly.express as px
import streamlit as st

from tools.dashboard.services.aggregations import (
    sample_courier_flow_atd,
    sla_buckets_by_merchant_surface,
    sla_rate_by_courier_flow,
)

_GREEN = "#06C167"
_GOLD = "#FFD700"
_RED = "#FF4B4B"
_BLACK = "#000000"
_SLA_MIN = 45.0

_BUCKET_COLORS = {
    "<30 min": "#06C167",
    "30-45 min": "#FFD700",
    "45-60 min": "#FF8C00",
    ">60 min": "#FF4B4B",
}

_BOX_PALETTE = [
    "#06C167",
    "#FFD700",
    "#000000",
    "#888888",
    "#444444",
    "#aaaaaa",
]


def _apply_defaults(fig, title: str) -> None:
    """Apply standard white-background layout to *fig*."""
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_color=_BLACK,
        title_font_size=16,
        title_font_color=_BLACK,
        title_text=title,
    )


def render_delivery_analysis(df: pd.DataFrame) -> None:
    """Render Tab 3: courier flow and merchant surface ATD charts.

    Four charts:
    1. ATD distribution box plot by courier flow (full width).
    2. SLA pass rate by courier flow (horizontal bar).
    3. Volume vs SLA rate bubble chart (courier flow).
    4. SLA bucket breakdown by merchant surface (horizontal
       stacked bar, full width).

    Args:
        df: Filtered DataFrame.
    """
    # ------------------------------------------------------------------
    # Chart 1 — ATD Distribution Box Plot (full width)
    # ------------------------------------------------------------------
    sample = sample_courier_flow_atd(df)
    fig_box = px.box(
        sample,
        x="courier_flow",
        y="ATD",
        color="courier_flow",
        color_discrete_sequence=_BOX_PALETTE,
        labels={
            "courier_flow": "Courier Flow",
            "ATD": "ATD (min)",
        },
    )
    fig_box.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Median: %{median:.2f} min<br>"
            "Q1: %{q1:.2f} min<br>"
            "Q3: %{q3:.2f} min<br>"
            "Lower fence: %{lowerfence:.2f} min<br>"
            "Upper fence: %{upperfence:.2f} min"
            "<extra></extra>"
        ),
    )
    fig_box.add_hline(
        y=_SLA_MIN,
        line_dash="dash",
        line_color=_RED,
        annotation_text="SLA 45 min",
        annotation_position="top right",
        annotation_font_color=_RED,
    )
    _apply_defaults(
        fig_box, "ATD Distribution by Courier Flow"
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Row 2 — SLA Pass Rate + Volume vs SLA Bubble
    # ------------------------------------------------------------------
    left, right = st.columns(2)

    sla_cf = sla_rate_by_courier_flow(df, sla_min=_SLA_MIN)

    # Chart 2 — SLA Pass Rate horizontal bar
    fig_sla = px.bar(
        sla_cf,
        x="sla_rate",
        y="courier_flow",
        orientation="h",
        color="sla_rate",
        color_continuous_scale=[_RED, _GOLD, _GREEN],
        range_color=[50, 100],
        text="sla_rate",
        labels={
            "sla_rate": "SLA Pass Rate (%)",
            "courier_flow": "",
        },
    )
    fig_sla.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "SLA Pass Rate: %{x:.2f}%"
            "<extra></extra>"
        ),
    )
    fig_sla.add_vline(
        x=80,
        line_dash="dash",
        line_color=_BLACK,
        annotation_text="80% target",
        annotation_position="top right",
    )
    _apply_defaults(
        fig_sla,
        "SLA Pass Rate by Courier Flow (\u226445 min)",
    )
    fig_sla.update_layout(coloraxis_showscale=False)
    left.plotly_chart(fig_sla, use_container_width=True)

    # Chart 3 — Volume vs SLA Rate bubble
    fig_bub = px.scatter(
        sla_cf,
        x="trip_count",
        y="sla_rate",
        size="mean_atd",
        color="sla_rate",
        color_continuous_scale=[_RED, _GOLD, _GREEN],
        range_color=[50, 100],
        text="courier_flow",
        custom_data=["mean_atd"],
        labels={
            "trip_count": "Trip Volume",
            "sla_rate": "SLA Pass Rate (%)",
            "mean_atd": "Mean ATD (min)",
        },
    )
    fig_bub.update_traces(
        textposition="top center",
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Trip Volume: %{x:,} trips<br>"
            "SLA Rate: %{y:.2f}%<br>"
            "Mean ATD: %{customdata[0]:.2f} min"
            "<extra></extra>"
        ),
    )
    fig_bub.add_hline(
        y=80,
        line_dash="dash",
        line_color=_BLACK,
        annotation_text="80% SLA target",
        annotation_position="bottom right",
    )
    _apply_defaults(
        fig_bub, "Volume vs SLA Rate by Courier Flow"
    )
    fig_bub.update_layout(coloraxis_showscale=False)
    right.plotly_chart(fig_bub, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Chart 4 — Horizontal Stacked SLA Buckets by Merchant Surface
    # ------------------------------------------------------------------
    ms_buckets = sla_buckets_by_merchant_surface(df)
    bucket_order = [
        "<30 min",
        "30-45 min",
        "45-60 min",
        ">60 min",
    ]
    fig_ms = px.bar(
        ms_buckets,
        y="merchant_surface",
        x="pct",
        color="bucket",
        barmode="stack",
        orientation="h",
        category_orders={"bucket": bucket_order},
        color_discrete_map=_BUCKET_COLORS,
        custom_data=["count"],
        labels={
            "merchant_surface": "Merchant Surface",
            "pct": "% of Trips",
            "bucket": "ATD Bucket",
        },
    )
    fig_ms.update_traces(
        hovertemplate=(
            "%{y}<br>"
            "%{fullData.name}: %{x:.2f}%%"
            " (%{customdata[0]:,} trips)"
            "<extra></extra>"
        )
    )
    fig_ms.add_vline(
        x=80,
        line_dash="dash",
        line_color=_BLACK,
        annotation_text="80% within SLA",
        annotation_position="top right",
    )
    _apply_defaults(
        fig_ms, "SLA Buckets by Merchant Surface"
    )
    st.plotly_chart(fig_ms, use_container_width=True)
