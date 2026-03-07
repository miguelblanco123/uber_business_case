"""Tab 5 — Distance Analysis: distance impact on ATD."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.dashboard.services.aggregations import (
    atd_by_distance_bins,
    scatter_pickup_dropoff_atd,
    sla_rate_by_distance_bins,
)
from tools.dashboard.services.metrics import SLA_THRESHOLD_MIN

_GREEN = "#06C167"
_GOLD = "#FFD700"
_RED = "#FF4B4B"
_BLACK = "#000000"


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


def render_distance_analysis(df: pd.DataFrame) -> None:
    """Render Tab 5: distance vs ATD charts.

    Four charts:
    1. Grouped bar — mean ATD by pickup vs dropoff distance bins,
       side-by-side (full width).
    2. SLA pass rate by pickup distance bins (left).
    3. SLA pass rate by dropoff distance bins (right).
    4. Pickup vs dropoff distance scatter, coloured by ATD
       (full width).

    Args:
        df: Filtered DataFrame.
    """
    # ------------------------------------------------------------------
    # Chart 1 — Grouped bar: pickup vs dropoff distance → mean ATD
    # ------------------------------------------------------------------
    pickup_bins = atd_by_distance_bins(df, "pickup_distance")
    dropoff_bins = atd_by_distance_bins(df, "dropoff_distance")

    fig_group = go.Figure()
    fig_group.add_trace(
        go.Bar(
            name="Pickup Distance",
            x=pickup_bins["bin_label"],
            y=pickup_bins["mean_atd"],
            marker_color=_GREEN,
            customdata=pickup_bins[["trip_count"]].values,
            hovertemplate=(
                "Pickup bin: %{x}<br>"
                "Mean ATD: %{y:.1f} min<br>"
                "Trips: %{customdata[0]:,}"
                "<extra></extra>"
            ),
        )
    )
    fig_group.add_trace(
        go.Bar(
            name="Dropoff Distance",
            x=dropoff_bins["bin_label"],
            y=dropoff_bins["mean_atd"],
            marker_color=_GOLD,
            customdata=dropoff_bins[["trip_count"]].values,
            hovertemplate=(
                "Dropoff bin: %{x}<br>"
                "Mean ATD: %{y:.1f} min<br>"
                "Trips: %{customdata[0]:,}"
                "<extra></extra>"
            ),
        )
    )
    fig_group.add_hline(
        y=SLA_THRESHOLD_MIN,
        line_dash="dash",
        line_color=_RED,
        annotation_text="SLA 45 min",
        annotation_position="top right",
        annotation_font_color=_RED,
    )
    fig_group.update_layout(
        **_base_layout(
            "Mean ATD by Pickup vs Dropoff Distance Bins"
        ),
        barmode="group",
        xaxis_title="Distance Range (km)",
        yaxis_title="Mean ATD (min)",
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig_group, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Row 2: SLA pass rate by pickup (left) and dropoff (right) bins
    # ------------------------------------------------------------------
    left, right = st.columns(2)

    # Chart 2 — SLA pass rate by pickup distance
    sla_pu = sla_rate_by_distance_bins(df, "pickup_distance")
    pu_colors = [
        _GREEN if v >= 80 else _RED for v in sla_pu["sla_rate"]
    ]
    fig_sla_pu = go.Figure(
        go.Bar(
            x=sla_pu["bin_label"],
            y=sla_pu["sla_rate"],
            marker_color=pu_colors,
            customdata=sla_pu[["mean_atd", "trip_count"]].values,
            hovertemplate=(
                "Pickup bin: %{x}<br>"
                "SLA Rate: %{y:.1f}%<br>"
                "Mean ATD: %{customdata[0]:.1f} min<br>"
                "Trips: %{customdata[1]:,}"
                "<extra></extra>"
            ),
            text=sla_pu["sla_rate"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )
    fig_sla_pu.add_hline(
        y=80,
        line_dash="dash",
        line_color=_BLACK,
        annotation_text="80% target",
        annotation_position="bottom right",
    )
    fig_sla_pu.update_layout(
        **_base_layout("SLA Pass Rate by Pickup Distance"),
        xaxis_title="Pickup Distance Range (km)",
        yaxis_title="SLA Pass Rate (%)",
        yaxis=dict(range=[0, 115]),
        showlegend=False,
    )
    left.plotly_chart(fig_sla_pu, use_container_width=True)

    # Chart 3 — SLA pass rate by dropoff distance
    sla_do = sla_rate_by_distance_bins(df, "dropoff_distance")
    do_colors = [
        _GREEN if v >= 80 else _RED for v in sla_do["sla_rate"]
    ]
    fig_sla_do = go.Figure(
        go.Bar(
            x=sla_do["bin_label"],
            y=sla_do["sla_rate"],
            marker_color=do_colors,
            customdata=sla_do[["mean_atd", "trip_count"]].values,
            hovertemplate=(
                "Dropoff bin: %{x}<br>"
                "SLA Rate: %{y:.1f}%<br>"
                "Mean ATD: %{customdata[0]:.1f} min<br>"
                "Trips: %{customdata[1]:,}"
                "<extra></extra>"
            ),
            text=sla_do["sla_rate"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )
    fig_sla_do.add_hline(
        y=80,
        line_dash="dash",
        line_color=_BLACK,
        annotation_text="80% target",
        annotation_position="bottom right",
    )
    fig_sla_do.update_layout(
        **_base_layout("SLA Pass Rate by Dropoff Distance"),
        xaxis_title="Dropoff Distance Range (km)",
        yaxis_title="SLA Pass Rate (%)",
        yaxis=dict(range=[0, 115]),
        showlegend=False,
    )
    right.plotly_chart(fig_sla_do, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Chart 4 — Pickup vs Dropoff scatter, coloured by ATD
    # ------------------------------------------------------------------
    sample = scatter_pickup_dropoff_atd(df)
    fig_scatter = go.Figure(
        go.Scatter(
            x=sample["pickup_distance"],
            y=sample["dropoff_distance"],
            mode="markers",
            marker=dict(
                color=sample["ATD"],
                colorscale=[
                    [0.0, _GREEN],
                    [0.5, _GOLD],
                    [1.0, _RED],
                ],
                cmin=0,
                cmax=90,
                size=4,
                opacity=0.5,
                colorbar=dict(
                    title="ATD (min)",
                    tickvals=[0, 45, 90],
                    ticktext=["0", "45 (SLA)", "90+"],
                ),
            ),
            customdata=sample[["ATD"]].values,
            hovertemplate=(
                "Pickup: %{x:.2f} km<br>"
                "Dropoff: %{y:.2f} km<br>"
                "ATD: %{customdata[0]:.1f} min"
                "<extra></extra>"
            ),
        )
    )
    fig_scatter.update_layout(
        **_base_layout(
            "Pickup vs Dropoff Distance, Coloured by ATD"
            "  (sample 5 000 trips)"
        ),
        xaxis_title="Pickup Distance (km)",
        yaxis_title="Dropoff Distance (km)",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
