from typing import Iterable

import pandas as pd


def expand_with_ancestors(hs_all_levels: pd.DataFrame, hscodes: Iterable) -> pd.DataFrame:
    current_codes = set(hs_all_levels.loc[hs_all_levels["hscode"].isin(hscodes), "hscode"].unique())

    changed = True
    while changed:
        changed = False
        parents = hs_all_levels.loc[
            hs_all_levels["hscode"].isin(current_codes), "parent"
        ].dropna().unique()
        missing = [p for p in parents if p not in current_codes]
        if missing:
            current_codes.update(missing)
            changed = True

    return hs_all_levels[hs_all_levels["hscode"].isin(current_codes)]
