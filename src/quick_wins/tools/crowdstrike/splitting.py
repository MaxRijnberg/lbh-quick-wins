import math
from typing import List

import pandas as pd


def chunk_df(df: pd.DataFrame, rows_per_chunk: int) -> List[pd.DataFrame]:
    if rows_per_chunk <= 0:
        raise ValueError("rows_per_chunk must be > 0")
    return [df.iloc[i : i + rows_per_chunk] for i in range(0, len(df), rows_per_chunk)]


def split_unit_tables(df_unit: pd.DataFrame, rows_per_table: int) -> List[pd.DataFrame]:
    # Optionally sort here if you want deterministic table ordering
    return chunk_df(df_unit, rows_per_table)


def num_tables_for_unit(df_unit: pd.DataFrame, rows_per_table: int) -> int:
    return int(math.ceil(len(df_unit) / rows_per_table)) if rows_per_table > 0 else 0
