import re

import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from typing import cast

from quick_wins.config.hs_codes_config import (
    DDGS_HS_CODE,
    HIGH_CONF_SCORE,
    KEYWORD_HS_OVERRIDES,
    KEYWORD_OVERRIDE_EXCLUSION_PATTERN,
    MIN_MARGIN,
    NON_SPECIFIC_CARGO_TERMS,
)
from quick_wins.tools.hs_codes.category_mapping import candidate_mask


def model_slug(model_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")


_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9 ]")


def is_non_specific_cargo(name: str) -> bool:
    normalized = _NON_ALNUM_SPACE.sub("", str(name).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized in NON_SPECIFIC_CARGO_TERMS


_KEYWORD_OVERRIDE_PATTERN = re.compile(
    r"\b("
    + "|".join(
        re.escape(k) for k in sorted(KEYWORD_HS_OVERRIDES, key=len, reverse=True)
    )
    + r")\b",
    re.IGNORECASE,
)

_DDGS_PATTERN = re.compile(r"\bdistillers dried grains with solubles\b", re.IGNORECASE)

_OVERRIDE_EXCLUSION_PATTERN = re.compile(
    KEYWORD_OVERRIDE_EXCLUSION_PATTERN, re.IGNORECASE
)


def keyword_override(cargo_text: str) -> str | None:
    text = str(cargo_text)
    if _DDGS_PATTERN.search(text):
        return DDGS_HS_CODE
    if _OVERRIDE_EXCLUSION_PATTERN.search(text):
        return None
    match = _KEYWORD_OVERRIDE_PATTERN.search(text)
    return KEYWORD_HS_OVERRIDES[match.group(0).upper()] if match else None


def similarity_matrix(
    cargo_embeddings: np.ndarray, hs_embeddings: np.ndarray
) -> np.ndarray:
    return normalize(cargo_embeddings) @ normalize(hs_embeddings).T


def match_cargo_to_hs(
    cargo_df: pd.DataFrame,
    hs_df: pd.DataFrame,
    sim_matrix: np.ndarray,
) -> pd.DataFrame:
    desc_by_code = dict(
        zip(hs_df["hscode"].astype(str).str.zfill(6), hs_df["description"])
    )

    rows = []
    for i, row in enumerate(cargo_df.itertuples()):
        # Checked before any embedding similarity - see KEYWORD_HS_OVERRIDES
        # for why (a small, deliberately curated set of terms where semantic
        # search kept losing to a false attractor no matter how the HS
        # description text was phrased).
        override_code = keyword_override(cast(str, row.cargo_text))
        if override_code is not None:
            rows.append(
                {
                    "name": row.name,
                    "commodityGroup": row.commodityGroup,
                    "cargo_text": row.cargo_text,
                    "n_rows": row.n_rows,
                    "hs_code_1": override_code,
                    "hs_desc_1": desc_by_code.get(override_code, ""),
                    "score_1": 1.0,
                    "score_2": 0.0,
                    "restricted_to_category": False,
                    "confidence": "high",
                    "keyword_override": True,
                }
            )
            continue

        commodity_group = str(row.commodityGroup_clean)
        mask = candidate_mask(hs_df, commodity_group)
        restricted = bool(mask.any() and mask.sum() < len(hs_df))
        sims = np.where(mask, sim_matrix[i], -1.0) if mask.any() else sim_matrix[i]

        # Top-2, not just top-1: a lone score threshold can't tell a clear
        # winner from a coin-flip tie (e.g. "Coal" scored anthracite and
        # bituminous within 0.0003 of each other) - the margin between the
        # top two candidates is what actually signals real confidence.
        top_idx = np.argsort(sims)[-2:][::-1]
        score_1, score_2 = sims[top_idx[0]], sims[top_idx[1]]
        confidence = (
            "high"
            if (score_1 >= HIGH_CONF_SCORE and (score_1 - score_2) >= MIN_MARGIN)
            else "needs_review"
        )
        # Shipment-admin placeholders ("General Cargo", "multiple parcel's")
        # carry no real commodity signal, so a "high" score against them is
        # a coincidence, not a real match - see NON_SPECIFIC_CARGO_TERMS.
        if confidence == "high" and is_non_specific_cargo(cast(str, row.name)):
            confidence = "needs_review"

        rows.append(
            {
                "name": row.name,
                "commodityGroup": row.commodityGroup,
                "cargo_text": row.cargo_text,
                "n_rows": row.n_rows,
                "hs_code_1": hs_df.iloc[top_idx[0]]["hscode"],
                "hs_desc_1": hs_df.iloc[top_idx[0]]["description"],
                "score_1": score_1,
                "score_2": score_2,
                "restricted_to_category": restricted,
                "confidence": confidence,
                "keyword_override": False,
            }
        )
    return pd.DataFrame(rows)
