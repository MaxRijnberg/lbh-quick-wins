import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from typing import Optional, Sequence


def stacked_risk_by_unit(df: pd.DataFrame) -> None:
    levels = ["Critical", "High", "Medium", "Low", "Unknown"]

    # Optional: ensure numeric
    for c in levels + ["Count"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # Aggregate across products within each unit
    agg = df.groupby("unit", as_index=False)[levels].sum()

    # (Optional) Sort units by total risk
    agg["Total"] = agg[levels].sum(axis=1)
    agg = agg.sort_values("Total", ascending=False)

    x_units = agg["unit"]

    # Build stacked bars
    fig = go.Figure()
    colours = {
        "Critical": "#d62728",
        "High": "#ff7f0e",
        "Medium": "#bcbd22",
        "Low": "#2ca02c",
        "Unknown": "#7f7f7f",
    }

    for lvl in levels:
        fig.add_trace(
            go.Bar(
                name=lvl,
                x=x_units,
                y=agg[lvl],
                marker_color=colours.get(lvl, None),
            )
        )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Unit",
        yaxis_title="Number of risks",
        legend_title="Risk level",
        height=450,
        margin=dict(l=40, r=20, t=20, b=60),
    )

    st.plotly_chart(fig, width="stretch")


def _trendline_figure(df: pd.DataFrame, metric_col: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    for unit in sorted(df["unit"].unique()):
        unit_df = df[df["unit"] == unit].sort_values("upload_date")
        fig.add_trace(
            go.Scatter(
                x=unit_df["upload_date"],
                y=unit_df[metric_col],
                mode="lines+markers",
                name=unit,
            )
        )

    fig.update_layout(
        xaxis_title="Upload date",
        yaxis_title=y_title,
        legend_title="Unit",
        height=400,
        margin=dict(l=40, r=20, t=20, b=60),
    )
    return fig


def vulnerability_trendline(
    history_df: pd.DataFrame, selected_units: Optional[Sequence[str]] = None
) -> None:
    """Renders separate Critical and High trendlines, one line per unit."""
    if history_df.empty:
        st.info("No history yet - upload a zip to start building the trendline.")
        return

    df = history_df.copy()
    df["upload_date"] = pd.to_datetime(df["upload_date"])

    if selected_units is not None:
        df = df[df["unit"].isin(selected_units)]

    if df.empty:
        st.info("No data for the selected countries.")
        return

    st.plotly_chart(_trendline_figure(df, "critical", "Critical vulnerabilities"), width="stretch")
    st.plotly_chart(_trendline_figure(df, "high", "High vulnerabilities"), width="stretch")
