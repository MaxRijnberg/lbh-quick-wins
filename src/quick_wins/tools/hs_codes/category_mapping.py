import numpy as np
import pandas as pd

from quick_wins.config.hs_codes_config import GROUP_TO_CHAPTERS


def add_chapter_column(hs: pd.DataFrame) -> pd.DataFrame:
    df = hs.copy()
    df["chapter"] = df["hscode"].astype(str).str.zfill(6).str[:2]
    return df


def candidate_mask(hs: pd.DataFrame, commodity_group: str) -> np.ndarray:
    chapters = GROUP_TO_CHAPTERS.get(commodity_group.strip().lower())
    if not chapters:
        return np.ones(len(hs), dtype=bool)
    return hs["chapter"].isin(chapters).to_numpy()
