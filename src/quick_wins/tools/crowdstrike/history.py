from __future__ import annotations

import pandas as pd

from pathlib import Path

from quick_wins.config.crowdstike_config import HISTORY_PATH

HISTORY_COLUMNS = ["upload_date", "unit", "critical", "high"]


def aggregate_critical_high_by_unit(
    df: pd.DataFrame, upload_date: str | None = None
) -> pd.DataFrame:
    """Sum Critical/High counts by unit (country) for one parsed upload."""
    if upload_date is None:
        upload_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    working = df.copy()
    for col in ("Critical", "High"):
        working[col] = pd.to_numeric(working[col], errors="coerce").fillna(0).astype(int)

    agg = working.groupby("unit", as_index=False)[["Critical", "High"]].sum()
    agg = agg.rename(columns={"Critical": "critical", "High": "high"})
    agg.insert(0, "upload_date", upload_date)
    return agg[HISTORY_COLUMNS]


def append_to_history(agg_df: pd.DataFrame, history_path: Path = HISTORY_PATH) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not history_path.exists()
    agg_df.to_csv(history_path, mode="a", header=write_header, index=False)


def load_history(history_path: Path = HISTORY_PATH) -> pd.DataFrame:
    if not history_path.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    return pd.read_csv(history_path, parse_dates=["upload_date"])
