import re
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize

from quick_wins.config.hs_codes_config import HIGH_CONF_SCORE, MIN_MARGIN
from quick_wins.tools.hs_codes.category_mapping import candidate_mask


def model_slug(model_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")


def similarity_matrix(
    cargo_embeddings: np.ndarray, hs_embeddings: np.ndarray
) -> np.ndarray:
    return normalize(cargo_embeddings) @ normalize(hs_embeddings).T


def match_cargo_to_hs(
    cargo_df: pd.DataFrame,
    hs_df: pd.DataFrame,
    sim_matrix: np.ndarray,
    top_k: int = 3,
) -> pd.DataFrame:
    rows = []
    for i, row in enumerate(cargo_df.itertuples()):
        commodity_group = str(row.commodityGroup_clean)
        mask = candidate_mask(hs_df, commodity_group)
        restricted = bool(mask.any() and mask.sum() < len(hs_df))
        sims = np.where(mask, sim_matrix[i], -1.0) if mask.any() else sim_matrix[i]

        top_idx = np.argsort(sims)[-top_k:][::-1]
        top1, top2 = sims[top_idx[0]], sims[top_idx[1]]
        confidence = (
            "high"
            if (top1 >= HIGH_CONF_SCORE and (top1 - top2) >= MIN_MARGIN)
            else "needs_review"
        )

        rows.append(
            {
                "cargo_text": row.cargo_text,
                "n_rows": row.n_rows,
                "hs_code_1": hs_df.iloc[top_idx[0]]["hscode"],
                "hs_desc_1": hs_df.iloc[top_idx[0]]["description"],
                "score_1": top1,
                "hs_code_2": hs_df.iloc[top_idx[1]]["hscode"],
                "hs_desc_2": hs_df.iloc[top_idx[1]]["description"],
                "score_2": top2,
                "restricted_to_category": restricted,
                "confidence": confidence,
            }
        )
    return pd.DataFrame(rows)


def match_cargo_to_hs_ensemble(
    cargo_df: pd.DataFrame,
    hs_df: pd.DataFrame,
    sim_matrices: Dict[str, np.ndarray],
    top_k: int = 3,
) -> pd.DataFrame:
    """A cargo description is "high" confidence only if every model's
    top-1 HS code agrees - agreement across independently-trained models
    is a stronger signal than any single model's own similarity score."""
    model_names = list(sim_matrices.keys())
    rows = []
    for i, row in enumerate(cargo_df.itertuples()):
        commodity_group = str(row.commodityGroup_clean)
        mask = candidate_mask(hs_df, commodity_group)
        restricted = bool(mask.any() and mask.sum() < len(hs_df))

        per_model = {}
        for name in model_names:
            sims = sim_matrices[name][i]
            sims = np.where(mask, sims, -1.0) if mask.any() else sims
            top_idx = np.argsort(sims)[-top_k:][::-1]
            per_model[name] = {
                "hs_code": hs_df.iloc[top_idx[0]]["hscode"],
                "hs_desc": hs_df.iloc[top_idx[0]]["description"],
                "score": float(sims[top_idx[0]]),
            }

        codes = {per_model[name]["hs_code"] for name in model_names}
        agreement = len(codes) == 1
        primary = model_names[0]

        result = {
            "cargo_text": row.cargo_text,
            "n_rows": row.n_rows,
            "hs_code_1": per_model[primary]["hs_code"],
            "hs_desc_1": per_model[primary]["hs_desc"],
            "restricted_to_category": restricted,
            "agreement": agreement,
            "confidence": "high" if agreement else "needs_review",
        }
        for name in model_names:
            key = model_slug(name)
            result[f"hs_code_{key}"] = per_model[name]["hs_code"]
            result[f"score_{key}"] = per_model[name]["score"]
        rows.append(result)
    return pd.DataFrame(rows)
