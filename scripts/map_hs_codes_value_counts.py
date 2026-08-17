import argparse
import logging

import pandas as pd
from sentence_transformers import SentenceTransformer

from quick_wins.config.hs_codes_config import (
    DATA_DIR,
    EMBEDDING_CACHE_DIR,
    EMBEDDING_MODEL,
    HS_TEXT_VERSION,
    QUERY_INSTRUCTION,
)
from quick_wins.tools.hs_codes import (
    import_bq_value_counts,
    import_hs_data,
    clean_bq_data,
    aggregate_cargo_value_counts,
    add_chapter_column,
    build_hs_encoding_text,
    cached_encode,
    similarity_matrix,
    match_cargo_to_hs,
)
from quick_wins.tools.hs_codes.text_cleaning import to_encoding_text
from quick_wins.tools.hs_codes.matching import model_slug
from quick_wins.utils.custom_errors import RunningError
from quick_wins.utils.loggers import get_logger
from quick_wins.utils.version_control import get_most_recent_version

NAME = "Generate value-count mapping"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=NAME)
    parser.add_argument(
        "-l",
        "--logging_level",
        required=False,
        choices=["debug", "info", "warn", "error", "critical"],
        help='Standard for logging level, will default to "info".',
        default="info",
    )
    parser.add_argument(
        "-f",
        "--output_filename",
        required=False,
        help='The file to output the commodity mapping to, default `Mapping HS codes value counts`. The ".xlsx" will append automatically.',
        default="Mapping HS codes value counts",
    )
    return parser.parse_args()


def main(args: argparse.Namespace, logger: logging.Logger) -> None:
    logger.info("Loading BQ value-count and HS reference data")
    bq_vc = import_bq_value_counts()
    total_occurrences = int(bq_vc["value_count"].sum())
    logger.info(
        f"{len(bq_vc)} distinct name/commodityGroup rows loaded, "
        f"{total_occurrences:,} total occurrences across the 3-year window"
    )

    hs_all = import_hs_data()
    hs = hs_all[hs_all["level"] == 6].reset_index(drop=True)

    logger.info("Cleaning and aggregating cargo descriptions by value count")
    bq_clean = clean_bq_data(bq_vc)
    n_unparseable = int(bq_clean["is_unparseable"].sum())
    if n_unparseable:
        unparseable_occurrences = int(
            bq_clean.loc[bq_clean["is_unparseable"], "value_count"].sum()
        )
        logger.warning(
            f"Flagged {n_unparseable} rows as unparseable (garbled/non-Latin text), "
            f"representing {unparseable_occurrences:,} occurrences"
        )

    bq_agg = aggregate_cargo_value_counts(bq_clean)
    logger.info(
        f"{len(bq_clean)} raw rows -> {len(bq_agg)} unique, parseable cargo "
        f"descriptions ({bq_agg['n_rows'].sum():,} total occurrences represented, "
        f"after merging text variants like 'Coal'/'COAL'/'coal' that clean to the same text)"
    )

    hs_chaptered = add_chapter_column(hs)

    logger.info(f"Loading embedding model {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    hs_cache_path = EMBEDDING_CACHE_DIR / f"hs_{model_slug(EMBEDDING_MODEL)}_{HS_TEXT_VERSION}.npy"
    logger.info(f"Encoding/loading {len(hs_chaptered)} HS descriptions (cache: {hs_cache_path})")
    hs_embeddings = cached_encode(
        model,
        build_hs_encoding_text(hs_chaptered),
        hs_cache_path,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    logger.info(f"Encoding {len(bq_agg)} cargo descriptions")
    query_texts = [QUERY_INSTRUCTION + to_encoding_text(t) for t in bq_agg["cargo_text"]]
    cargo_embeddings = model.encode(
        query_texts,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    sim_matrix = similarity_matrix(cargo_embeddings, hs_embeddings)

    logger.info("Matching cargo descriptions to HS codes")
    df_results = match_cargo_to_hs(bq_agg, hs_chaptered, sim_matrix)
    df_results = df_results.rename(columns={"n_rows": "value_count"})

    n_review = int((df_results["confidence"] == "needs_review").sum())
    n_review_occurrences = int(
        df_results.loc[df_results["confidence"] == "needs_review", "value_count"].sum()
    )
    logger.info(
        f"{n_review}/{len(df_results)} unique cargo descriptions need manual review "
        f"({n_review_occurrences:,}/{int(df_results['value_count'].sum()):,} total occurrences)"
    )

    unparseable = bq_clean.loc[
        bq_clean["is_unparseable"], ["name", "commodityGroup", "value_count"]
    ]

    version = get_most_recent_version(DATA_DIR, args.output_filename, ".xlsx") + 1
    out_path = DATA_DIR / f"{args.output_filename}_v{version}.xlsx"

    logger.info(f"Writing mapping to {out_path}")
    with pd.ExcelWriter(out_path) as writer:
        df_results.sort_values("value_count", ascending=False).to_excel(
            writer, sheet_name="mapping", index=False
        )
        unparseable.sort_values("value_count", ascending=False).to_excel(
            writer, sheet_name="unparseable_flagged", index=False
        )


if __name__ == "__main__":
    args = parse_args()
    logger = get_logger(NAME, args.logging_level)
    logger.info(f"Starting script for {NAME}")
    try:
        main(args, logger)
    except Exception as e:
        logger.error(e)
        raise RunningError(e)
    else:
        logger.info(f"Finished script for {NAME}")
