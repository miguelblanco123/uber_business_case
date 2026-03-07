"""Tab 2 — Time Patterns: hourly combo chart and day×hour heatmap."""
import pandas as pd
import plotly.express as px
import streamlit as st
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from tools.dashboard.services.aggregations import (
    atd_by_hour,
    atd_heatmap,
    trips_by_hour,
)

_GREEN = "#06C167"
_HEATMAP_SCALE = ["#06C167", "#FFD700", "#000000"]
_SLA = 45

# AM/PM tick labels for hours 0-23
_HOUR_LABELS = (
    ["12 AM"]
    + [f"{h} AM" for h in range(1, 12)]
    + ["12 PM"]
    + [f"{h} PM" for h in range(1, 12)]
)
_HOUR_VALS = list(range(24))


def render_time_analysis(
    df: pd.DataFrame,
    df_historic: pd.DataFrame,
) -> None:
    """Render Tab 2: combo ATD+volume chart and day×hour heatmap.

    Args:
        df: Filtered DataFrame for the selected week.
        df_historic: All-time filtered DataFrame (same dimension
            filters, all dates) used for the historic ATD baseline.
    """
    # --- Combo: Volume bars + ATD lines (dual y-axis) ---
    hourly = atd_by_hour(df)
    hist_hourly = atd_by_hour(df_historic)
    vol = trips_by_hour(df)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Volume bars — primary y
    fig.add_trace(
        go.Bar(
            x=vol["hour_local"],
            y=vol["trip_count"],
            name="Trip Volume",
            marker_color=_GREEN,
            opacity=0.65,
            customdata=[
                _HOUR_LABELS[h] for h in vol["hour_local"]
            ],
            hovertemplate=(
                "%{customdata}<br>"
                "Trips: %{y:,} trips"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    # Current-week ATD — secondary y
    fig.add_trace(
        go.Scatter(
            x=hourly["hour_local"],
            y=hourly["mean_atd"],
            name="Mean ATD (week)",
            mode="lines+markers",
            line=dict(color="#000000", width=2),
            marker=dict(size=6),
            customdata=[
                _HOUR_LABELS[h] for h in hourly["hour_local"]
            ],
            hovertemplate=(
                "%{customdata}<br>"
                "Mean ATD: %{y:.2f} min"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    # Historic average ATD — secondary y
    fig.add_trace(
        go.Scatter(
            x=hist_hourly["hour_local"],
            y=hist_hourly["mean_atd"],
            name="Mean ATD (historic avg)",
            mode="lines",
            line=dict(color="#FF4B4B", width=1.5, dash="dash"),
            customdata=[
                _HOUR_LABELS[h]
                for h in hist_hourly["hour_local"]
            ],
            hovertemplate=(
                "%{customdata}<br>"
                "Historic ATD: %{y:.2f} min"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    # SLA reference line on secondary y
    # add_hline does not support secondary_y; use add_shape + add_annotation
    fig.add_shape(
        type="line",
        x0=0, x1=23,
        y0=_SLA, y1=_SLA,
        xref="x", yref="y2",
        line=dict(color="#FF4B4B", width=1, dash="dot"),
    )
    fig.add_annotation(
        x=23, y=_SLA,
        xref="x", yref="y2",
        text="<b>SLA 45 min</b>",
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        font=dict(size=11, color="#FF4B4B"),
        bgcolor="rgba(255,255,255,0.75)",
        borderpad=2,
    )

    fig.update_xaxes(
        title_text="Hour (local)",
        tickvals=_HOUR_VALS,
        ticktext=_HOUR_LABELS,
        tickangle=45,
    )
    fig.update_yaxes(
        title_text="Trip Volume",
        secondary_y=False,
        showgrid=True,
        gridcolor="#F0F0F0",
    )
    fig.update_yaxes(
        title_text="Mean ATD (min)",
        secondary_y=True,
        showgrid=False,
    )
    fig.update_layout(
        title="Trip Volume & Mean ATD by Local Hour",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_color="#000000",
        title_font_size=16,
        title_font_color="#000000",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        bargap=0.15,
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Day × Hour Heatmap (full width) ---
    pivot = atd_heatmap(df)
    pivot.columns = [_HOUR_LABELS[h] for h in pivot.columns]
    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=_HEATMAP_SCALE,
        text_auto=".1f",
        aspect="auto",
        title="Mean ATD by Day × Hour",
        labels={
            "x": "Hour (local)",
            "y": "Day",
            "color": "ATD (min)",
        },
    )
    fig_heat.update_traces(
        hovertemplate=(
            "Day: %{y}<br>"
            "%{x}<br>"
            "Mean ATD: %{z:.2f} min"
            "<extra></extra>"
        ),
    )

    fig_heat.update_xaxes(tickangle=45)
    fig_heat.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_color="#000000",
        title_font_size=16,
        title_font_color="#000000",
    )
    st.plotly_chart(fig_heat, use_container_width=True)
