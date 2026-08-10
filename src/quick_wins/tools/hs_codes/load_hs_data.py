import pandas as pd

from quick_wins.config.hs_codes_config import HS_PATH, BQ_PATH


def import_bq_data() -> pd.DataFrame:
    return pd.read_csv(BQ_PATH).drop(columns=["uniqueName"])


def import_hs_data() -> pd.DataFrame:
    return pd.read_csv(HS_PATH)
