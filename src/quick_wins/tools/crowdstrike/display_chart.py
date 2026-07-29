import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def stacked_risk_by_unit(df: pd.DataFrame):
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


# In your app:
# stacked_risk_by_unit(your_df)
