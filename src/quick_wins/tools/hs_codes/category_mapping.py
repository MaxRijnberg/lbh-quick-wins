import numpy as np
import pandas as pd

from quick_wins.config.hs_codes_config import GROUP_TO_CHAPTERS, HS_DESCRIPTION_SYNONYMS
from quick_wins.tools.hs_codes.text_cleaning import to_encoding_text


def add_chapter_column(hs: pd.DataFrame) -> pd.DataFrame:
    df = hs.copy()
    df["chapter"] = df["hscode"].astype(str).str.zfill(6).str[:2]
    return df


def candidate_mask(hs: pd.DataFrame, commodity_group: str) -> np.ndarray:
    chapters = GROUP_TO_CHAPTERS.get(commodity_group.strip().lower())
    if not chapters:
        return np.ones(len(hs), dtype=bool)
    return hs["chapter"].isin(chapters).to_numpy()


def build_hs_encoding_text(hs: pd.DataFrame) -> np.ndarray:
    """Text actually fed to the embedding model for each HS row - the raw
    legal description plus any HS_DESCRIPTION_SYNONYMS for that code. Formal
    HS wording often shares no vocabulary with how a commodity is named in
    trade (e.g. 271012 "light oils and preparations..." never says
    "gasoline"), which was letting semantically unrelated codes with more
    ordinary-sounding text win the similarity race - see the config comment
    on HS_DESCRIPTION_SYNONYMS for specifics."""
    codes = hs["hscode"].astype(str).str.zfill(6)
    synonyms = codes.map(HS_DESCRIPTION_SYNONYMS).fillna("")
    combined = (hs["description"].fillna("") + " " + synonyms).str.strip()
    return combined.map(to_encoding_text).to_numpy()
