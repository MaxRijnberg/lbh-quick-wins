import re
import unicodedata

import pandas as pd

# Cyrillic/other letters that are visually indistinguishable from Latin ones
# but break token/string matching (e.g. "сondensed" with a Cyrillic "с").
HOMOGLYPH_MAP = str.maketrans(
    {
        "с": "c", "С": "C", "е": "e", "Е": "E", "а": "a", "А": "A",
        "о": "o", "О": "O", "р": "p", "Р": "P", "х": "x", "Х": "X",
        "у": "y", "Н": "H", "В": "B", "К": "K", "М": "M", "Т": "T",
    }
)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    text = text.translate(HOMOGLYPH_MAP)
    return re.sub(r"\s+", " ", text).strip()


def is_mostly_latin(text: str, threshold: float = 0.6) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    latin = sum(1 for c in letters if c.isascii())
    return (latin / len(letters)) >= threshold


def build_cargo_text(name: str, group: str) -> str:
    if group and group.lower() not in name.lower():
        return f"{name} {group}".strip()
    return name.strip()


def clean_bq_data(bq: pd.DataFrame) -> pd.DataFrame:
    df = bq.copy()
    df["name_clean"] = df["name"].fillna("").map(clean_text)
    df["commodityGroup_clean"] = df["commodityGroup"].fillna("").map(clean_text)
    df["is_unparseable"] = ~df["name_clean"].map(is_mostly_latin)
    df["cargo_text"] = [
        build_cargo_text(n, g)
        for n, g in zip(df["name_clean"], df["commodityGroup_clean"])
    ]
    return df


def dedupe_cargo(df: pd.DataFrame) -> pd.DataFrame:
    parseable = df[~df["is_unparseable"]].copy()
    parseable["dedupe_key"] = parseable["cargo_text"].str.lower()
    counts = parseable.groupby("dedupe_key").size().rename("n_rows")
    return (
        parseable.drop_duplicates(subset="dedupe_key", keep="first")
        .join(counts, on="dedupe_key")
        .drop(columns="dedupe_key")
        .reset_index(drop=True)
    )
