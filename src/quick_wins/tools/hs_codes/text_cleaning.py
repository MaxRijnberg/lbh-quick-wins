import re
import unicodedata

import pandas as pd

from quick_wins.config.hs_codes_config import ABBREVIATIONS, COMMODITY_ALIASES, FILLER_PHRASES

# Cyrillic/other letters that are visually indistinguishable from Latin ones
# but break token/string matching (e.g. "сondensed" with a Cyrillic "с").
HOMOGLYPH_MAP = str.maketrans(
    {
        "с": "c", "С": "C", "е": "e", "Е": "E", "а": "a", "А": "A",
        "о": "o", "О": "O", "р": "p", "Р": "P", "х": "x", "Х": "X",
        "у": "y", "Н": "H", "В": "B", "К": "K", "М": "M", "Т": "T",
    }
)

_ABBREVIATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(ABBREVIATIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_FILLER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in sorted(FILLER_PHRASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_ALIAS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(COMMODITY_ALIASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Parenthetical content that's pure noise for classification: shipment/deal
# references ("(Parcel 2)", "(Lot 5)") and numeric-only asides ("(380)").
# Deliberately conservative - doesn't touch parens with real words in them
# (e.g. "(FUEL OIL)"), since the source data is heavily ALL-CAPS and "looks
# like a code" is too unreliable a signal to risk stripping genuine content.
_NUMERIC_PAREN_PATTERN = re.compile(r"\(\s*[\d\s.,\-/%]+\s*\)")
_DEAL_REF_PAREN_PATTERN = re.compile(
    r"\(\s*(?:parcel|lot|shipment|cargo|deal)\s*[\w.\-/]*\s*\)", re.IGNORECASE
)

# Standalone grade/quality-spec numbers (octane ratings, sulphur ppm figures,
# viscosity grades, parcel numbers) that don't change the 6-digit HS code.
_BARE_NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?%?")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    text = text.translate(HOMOGLYPH_MAP)
    return re.sub(r"\s+", " ", text).strip()


def expand_abbreviations(text: str) -> str:
    return _ABBREVIATION_PATTERN.sub(lambda m: ABBREVIATIONS[m.group(0).upper()], text)


def expand_commodity_aliases(text: str) -> str:
    return _ALIAS_PATTERN.sub(
        lambda m: f"{m.group(0)} {COMMODITY_ALIASES[m.group(0).upper()]}", text
    )


def remove_filler_words(text: str) -> str:
    text = _FILLER_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def remove_parenthetical_noise(text: str) -> str:
    text = _NUMERIC_PAREN_PATTERN.sub("", text)
    text = _DEAL_REF_PAREN_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def remove_bare_numbers(text: str) -> str:
    text = _BARE_NUMBER_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def to_encoding_text(text: str) -> str:
    return text.lower()


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
    df["name_clean"] = (
        df["name"]
        .fillna("")
        .map(clean_text)
        .map(expand_abbreviations)
        .map(expand_commodity_aliases)
        .map(remove_parenthetical_noise)
        .map(remove_bare_numbers)
        .map(remove_filler_words)
    )
    df["commodityGroup_clean"] = (
        df["commodityGroup"]
        .fillna("")
        .map(clean_text)
        .map(expand_abbreviations)
        .map(remove_parenthetical_noise)
        .map(remove_bare_numbers)
        .map(remove_filler_words)
    )
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


def aggregate_cargo_value_counts(
    df: pd.DataFrame, count_col: str = "value_count"
) -> pd.DataFrame:
    """Like dedupe_cargo, but for data that's already been grouped upstream
    (e.g. a BigQuery value_counts export) - text variants that clean down to
    the same cargo_text (e.g. "Coal"/"COAL"/"coal" as separate rows) get
    merged, summing their counts rather than just counting duplicate rows.
    The representative name/commodityGroup shown for each group is whichever
    original row had the highest count, not just whichever appeared first."""
    parseable = df[~df["is_unparseable"]].copy()
    parseable = parseable.sort_values(count_col, ascending=False)
    parseable["dedupe_key"] = parseable["cargo_text"].str.lower()
    counts = parseable.groupby("dedupe_key")[count_col].sum().rename("n_rows")
    return (
        parseable.drop_duplicates(subset="dedupe_key", keep="first")
        .drop(columns=[count_col])
        .join(counts, on="dedupe_key")
        .drop(columns="dedupe_key")
        .reset_index(drop=True)
    )
