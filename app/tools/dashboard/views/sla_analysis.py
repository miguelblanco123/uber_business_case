"""Tab 1 — Performance Overview: ATD distribution and SLA charts."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.dashboard.services.aggregations import (
    atd_daily_percentiles,
    atd_distribution,
    sla_buckets,
)
from tools.dashboard.services.metrics import SLA_THRESHOLD_MIN

_GREEN = "#06C167"
_GOLD = "#FFD700"
_ORANGE = "#FF8C00"
_RED = "#FF4B4B"
_BLACK = "#000000"
_GRAY = "#888888"

_BUCKET_COLORS = {
    "<30 min": "#06C167",
    "30-45 min": "#FFD700",
    "45-60 min": "#FF8C00",
    ">60 min": "#FF4B4B",
}


def _base_layout(title: str) -> dict:
    """Return a standard white-background Plotly layout dict."""
    return dict(
        title_text=title,
        title_font_size=16,
        title_font_color=_BLACK,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_color=_BLACK,
    )


def render_sla_analysis(df: pd.DataFrame) -> None:
    """Render Tab 1: Performance Overview charts.

    Five charts:
    1. ATD histogram with SLA zone shading and percentile
       annotations (left, wide).
    2. Enhanced SLA donut with centre SLA-rate annotation (right).
    3. Daily ATD trend — median line with P25–P75 shaded band
       (full width).
    4. Mean ATD by Geo Archetype — horizontal bars (left).
    5. Mean ATD by Territory, worst 10 — horizontal bars (right).

    Args:
        df: Filtered DataFrame.
    """
    # ------------------------------------------------------------------
    # Row 1: ATD Histogram (zone-shaded) + SLA Donut
    # ------------------------------------------------------------------
    left, right = st.columns([3, 2])

    dist = atd_distribution(df)

    # Chart 1 — ATD Histogram with coloured SLA zone backgrounds
    fig_hist = go.Figure()

    zones = [
        (0, 30, "rgba(6,193,103,0.09)", "< 30 min"),
        (30, 45, "rgba(255,215,0,0.13)", "30–45 min"),
        (45, 60, "rgba(255,140,0,0.13)", "45–60 min"),
        (60, 120, "rgba(255,75,75,0.10)", "> 60 min"),
    ]
    for x0, x1, fill, _ in zones:
        fig_hist.add_vrect(
            x0=x0, x1=x1,
            fillcolor=fill,
            layer="below",
            line_width=0,
        )

    fig_hist.add_trace(
        go.Histogram(
            x=dist["ATD"],
            nbinsx=60,
            marker_color=_GREEN,
            marker_opacity=0.85,
            name="ATD",
            hovertemplate=(
                "ATD: %{x} min<br>"
                "Count: %{y:,} trips"
                "<extra></extra>"
            ),
        )
    )

    _vlines = [
        (
            dist.attrs["p25"], "dot", _GRAY,
            f"P25 {dist.attrs['p25']:.1f} min", 0.97, "right",
        ),
        (
            dist.attrs["p50"], "dash", _GRAY,
            f"P50 {dist.attrs['p50']:.1f} min", 0.88, "right",
        ),
        (
            dist.attrs["p75"], "dot", _GRAY,
            f"P75 {dist.attrs['p75']:.1f} min", 0.79, "right",
        ),
        (
            SLA_THRESHOLD_MIN, "dash", _RED,
            "SLA 45 min", 0.97, "left",
        ),
    ]
    for x_val, dash, color, label, y_ref, anchor in _vlines:
        fig_hist.add_vline(
            x=x_val,
            line_dash=dash,
            line_color=color,
            line_width=1.5,
        )
        fig_hist.add_annotation(
            x=x_val,
            y=y_ref,
            xref="x",
            yref="paper",
            text=f"<b>{label}</b>",
            showarrow=False,
            xanchor=anchor,
            yanchor="top",
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.82)",
            borderpad=2,
        )

    fig_hist.update_layout(
        **_base_layout("ATD Distribution"),
        xaxis_title="ATD (minutes)",
        yaxis_title="Trips",
        xaxis=dict(range=[0, 120]),
        bargap=0.02,
        showlegend=False,
    )
    left.plotly_chart(fig_hist, use_container_width=True)

    # Chart 2 — SLA Donut with centre annotation
    buckets = sla_buckets(df)
    labels = buckets["bucket"].tolist()
    values = buckets["count"].tolist()
    colors = [_BUCKET_COLORS[b] for b in labels]

    total = sum(values)
    within_sla = sum(
        v for b, v in zip(labels, values)
        if b in ("<30 min", "30-45 min")
    )
    sla_pct = 100.0 * within_sla / total if total > 0 else 0.0

    fig_donut = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker_colors=colors,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value:,} trips · %{percent:.1%}"
                "<extra></extra>"
            ),
            textinfo="percent",
            textfont_size=12,
        )
    )
    fig_donut.add_annotation(
        text=(
            f"<b>{sla_pct:.1f}%</b><br>"
            "<span style='font-size:11px'>within SLA</span>"
        ),
        x=0.5,
        y=0.5,
        font_size=18,
        showarrow=False,
        font_color=_GREEN,
    )
    fig_donut.update_layout(
        **_base_layout("SLA Breakdown"),
        legend=dict(orientation="v", x=1.0, y=0.5),
    )
    right.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Chart 3 — Daily ATD Trend: median line + P25–P75 band
    # ------------------------------------------------------------------
    daily = atd_daily_percentiles(df)
    if not daily.empty and len(daily) > 1:
        daily["date_str"] = daily["date"].astype(str)

        fig_trend = go.Figure()

        # Lower bound (invisible, anchors the fill)
        fig_trend.add_trace(
            go.Scatter(
                x=daily["date_str"],
                y=daily["p25"],
                mode="lines",
                line_color="rgba(0,0,0,0)",
                showlegend=False,
                hoverinfo="skip",
                name="P25",
            )
        )
        # Upper bound fills down to previous trace
        fig_trend.add_trace(
            go.Scatter(
                x=daily["date_str"],
                y=daily["p75"],
                mode="lines",
                line_color="rgba(0,0,0,0)",
                fill="tonexty",
                fillcolor="rgba(6,193,103,0.18)",
                name="P25–P75 band",
                hoverinfo="skip",
            )
        )
        # Median line
        fig_trend.add_trace(
            go.Scatter(
                x=daily["date_str"],
                y=daily["p50"],
                mode="lines+markers",
                line=dict(color=_GREEN, width=2.5),
                marker=dict(size=7, color=_GREEN),
                name="Median ATD",
                customdata=daily[
                    ["trip_count", "p25", "p75"]
                ].values,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Median: %{y:.1f} min<br>"
                    "P25: %{customdata[1]:.1f} min<br>"
                    "P75: %{customdata[2]:.1f} min<br>"
                    "Trips: %{customdata[0]:,}"
                    "<extra></extra>"
                ),
            )
        )
        fig_trend.add_hline(
            y=SLA_THRESHOLD_MIN,
            line_dash="dash",
            line_color=_RED,
            annotation_text="SLA 45 min",
            annotation_position="bottom right",
            annotation_font_color=_RED,
        )
        fig_trend.update_layout(
            **_base_layout("Daily ATD Trend  (Median ± IQR)"),
            xaxis_title="Date",
            yaxis_title="ATD (min)",
            legend=dict(orientation="h", y=1.05),
            hovermode="x unified",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

