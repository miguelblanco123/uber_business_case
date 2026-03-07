"""Tab 4 — Geographic: territory and geo-archetype ATD charts."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from tools.dashboard.services.aggregations import (
    atd_by_geo_archetype,
    sample_geo_archetype_atd,
    territory_performance,
)

_GREEN = "#06C167"
_GOLD = "#FFD700"
_RED = "#FF4B4B"
_SEQ_SCALE = ["#06C167", "#FFD700", "#000000"]
_LAYOUT = dict(
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font_color="#000000",
    title_font_size=16,
    title_font_color="#000000",
)


def render_geo_analysis(df: pd.DataFrame) -> None:
    """Render Tab 4: geographic ATD analysis.

    Four charts:
    1. Territory performance matrix (volume vs ATD, SLA bubble).
    2. ATD IQR range by territory (p25–p75 band + median).
    3. SLA compliance rate by territory (color-coded bar).
    4. ATD distribution by geo archetype (box plot, full width).

    Args:
        df: Filtered DataFrame.
    """
    perf = territory_performance(df)
    n_terr = len(perf)
    bar_height = max(400, n_terr * 28)

    # ── G1: Territory Performance Matrix ─────────────────────────
    st.markdown("#### Territory Performance Matrix")
    st.caption(
        "Bubble size = SLA breach rate  ·  "
        "Colour = Mean ATD  ·  Dashed line = 45-min SLA"
    )
    perf["sla_breach"] = (100 - perf["sla_rate"]).clip(lower=0)
    fig_matrix = px.scatter(
        perf,
        x="trip_count",
        y="mean_atd",
        size="sla_breach",
        color="mean_atd",
        color_continuous_scale=_SEQ_SCALE,
        text="territory",
        size_max=55,
        title=(
            "Territory: Volume vs Mean ATD"
            " (bubble = SLA breach %)"
        ),
        labels={
            "trip_count": "Trip Volume",
            "mean_atd": "Mean ATD (min)",
            "sla_breach": "SLA Breach (%)",
        },
        custom_data=["sla_breach", "sla_rate", "trip_count"],
    )
    fig_matrix.update_traces(
        textposition="top center",
        marker=dict(
            opacity=0.8,
            line=dict(width=1, color="#000000"),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Trip Volume: %{customdata[2]:,.0f} trips<br>"
            "Mean ATD: %{y:.2f} min<br>"
            "SLA Breach: %{customdata[0]:.2f}%<br>"
            "SLA Rate: %{customdata[1]:.2f}%"
            "<extra></extra>"
        ),
    )
    fig_matrix.add_hline(
        y=45,
        line_dash="dash",
        line_color=_RED,
        annotation_text="SLA 45 min",
        annotation_position="bottom right",
        annotation_font_color=_RED,
    )
    fig_matrix.update_layout(
        **_LAYOUT,
        coloraxis_showscale=False,
        height=500,
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

    # ── Row 2: ATD range  |  SLA compliance ──────────────────────
    left2, right2 = st.columns([3, 2])

    # G2 — ATD IQR Range by Territory
    fig_range = go.Figure()
    fig_range.add_trace(
        go.Bar(
            x=perf["p75_atd"] - perf["p25_atd"],
            y=perf["territory"],
            base=perf["p25_atd"],
            orientation="h",
            marker_color=_GREEN,
            opacity=0.45,
            name="IQR (p25–p75)",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "p25: %{base:.2f} min<br>"
                "p75: %{customdata:.2f} min"
                "<extra></extra>"
            ),
            customdata=perf["p75_atd"],
        )
    )
    fig_range.add_trace(
        go.Scatter(
            x=perf["median_atd"],
            y=perf["territory"],
            mode="markers",
            marker=dict(
                color="#000000",
                size=9,
                symbol="line-ns-open",
                line=dict(width=2),
            ),
            name="Median ATD",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Median: %{x:.2f} min"
                "<extra></extra>"
            ),
        )
    )
    fig_range.add_vline(
        x=45,
        line_dash="dash",
        line_color=_RED,
        annotation_text="SLA 45 min",
        annotation_font_color=_RED,
    )
    fig_range.update_layout(
        **_LAYOUT,
        title="ATD IQR Range by Territory",
        xaxis_title="ATD (min)",
        yaxis_title="Territory",
        height=bar_height,
        legend=dict(orientation="h", y=1.06),
        barmode="overlay",
    )
    left2.plotly_chart(fig_range, use_container_width=True)

    # G3 — SLA Compliance by Territory
    perf_sla = perf.sort_values("sla_rate")
    bar_colors = [
        _GREEN if r >= 70 else (_GOLD if r >= 50 else _RED)
        for r in perf_sla["sla_rate"]
    ]
    fig_sla = go.Figure(
        go.Bar(
            x=perf_sla["sla_rate"],
            y=perf_sla["territory"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{r:.2f}%" for r in perf_sla["sla_rate"]],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "SLA Rate: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )
    fig_sla.add_vline(
        x=70,
        line_dash="dot",
        line_color="#000000",
        annotation_text="70% target",
    )
    fig_sla.update_layout(
        **_LAYOUT,
        title="SLA Compliance by Territory (% ≤ 45 min)",
        xaxis_title="% Trips within SLA",
        yaxis_title="",
        xaxis_range=[0, 115],
        height=bar_height,
    )
    right2.plotly_chart(fig_sla, use_container_width=True)

    # ── G4: ATD Distribution by Geo Archetype (full width) ───────
    sample = sample_geo_archetype_atd(df)
    geo_stats = atd_by_geo_archetype(df)
    geo_order = (
        geo_stats.sort_values("mean_atd")["geo_archetype"].tolist()
    )
    _BOX_COLORS = [
        _GREEN, _GOLD, "#000000", _RED, "#4BC8FF", "#A855F7",
    ]
    n_arch = len(geo_order)
    fig_box = px.box(
        sample,
        x="ATD",
        y="geo_archetype",
        orientation="h",
        color="geo_archetype",
        color_discrete_sequence=_BOX_COLORS,
        category_orders={"geo_archetype": geo_order},
        title="ATD Distribution by Geo Archetype",
        labels={
            "ATD": "ATD (min)",
            "geo_archetype": "Geo Archetype",
        },
    )
    fig_box.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "ATD: %{x:.2f} min"
            "<extra></extra>"
        ),
    )
    fig_box.add_vline(
        x=45,
        line_dash="dash",
        line_color=_RED,
        annotation_text="SLA 45 min",
        annotation_font_color=_RED,
    )
    fig_box.update_layout(
        **_LAYOUT,
        showlegend=False,
        height=max(380, n_arch * 60),
    )
    st.plotly_chart(fig_box, use_container_width=True)
