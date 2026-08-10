import argparse
import logging

import pandas as pd
from sentence_transformers import SentenceTransformer

from quick_wins.config.hs_codes_config import DATA_DIR, EMBEDDING_MODEL, QUERY_INSTRUCTION
from quick_wins.tools.hs_codes import (
    import_bq_data,
    import_hs_data,
    clean_bq_data,
    dedupe_cargo,
    add_chapter_column,
    similarity_matrix,
    match_cargo_to_hs,
    expand_with_ancestors,
)
from quick_wins.utils.custom_errors import RunningError
from quick_wins.utils.loggers import get_logger
from quick_wins.utils.version_control import get_most_recent_version

NAME = "Generate mapping"


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
        help='The file to output the commodity mapping to, default `Mapping HS codes`. The ".xlsx" will append automatically.',
        default="Mapping HS codes",
    )
    parser.add_argument(
        "-r",
        "--output_relevant_hs",
        required=False,
        help="Output the relevant HS codes in an Excel file saved as `HS-Codes vN.xlsx`.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-e",
        "--expand_hs_parents",
        required=False,
        help="Expand the HS codes to include their parents (e.g. 151519 -> 1515 -> 15).",
        action="store_true",
        default=False,
    )
    return parser.parse_args()


def main(args: argparse.Namespace, logger: logging.Logger) -> None:
    logger.info("Loading BQ and HS reference data")
    bq = import_bq_data()
    hs_all = import_hs_data()
    hs = hs_all[hs_all["level"] == 6].reset_index(drop=True)

    logger.info("Cleaning and deduplicating cargo descriptions")
    bq_clean = clean_bq_data(bq)
    n_unparseable = int(bq_clean["is_unparseable"].sum())
    if n_unparseable:
        logger.warning(
            f"Flagged {n_unparseable} rows as unparseable (garbled/non-Latin text)"
        )

    bq_unique = dedupe_cargo(bq_clean)
    logger.info(
        f"{len(bq_clean)} raw rows -> {len(bq_unique)} unique, parseable cargo "
        f"descriptions ({len(bq_clean) - len(bq_unique)} removed as duplicates/unparseable)"
    )

    hs_chaptered = add_chapter_column(hs)

    logger.info(f"Loading embedding model {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    logger.info(f"Encoding {len(hs_chaptered)} HS descriptions")
    hs_embeddings = model.encode(
        hs_chaptered["description"].fillna("").to_numpy(),
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    logger.info(f"Encoding {len(bq_unique)} cargo descriptions")
    query_texts = [QUERY_INSTRUCTION + t for t in bq_unique["cargo_text"]]
    cargo_embeddings = model.encode(
        query_texts,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    sim_matrix = similarity_matrix(cargo_embeddings, hs_embeddings)

    logger.info("Matching cargo descriptions to HS codes")
    df_results = match_cargo_to_hs(bq_unique, hs_chaptered, sim_matrix)

    n_review = int((df_results["confidence"] == "needs_review").sum())
    n_review_rows = int(
        df_results.loc[df_results["confidence"] == "needs_review", "n_rows"].sum()
    )
    logger.info(
        f"{n_review}/{len(df_results)} unique cargo descriptions need manual review "
        f"({n_review_rows} underlying rows)"
    )

    unparseable = bq_clean.loc[bq_clean["is_unparseable"], ["name", "commodityGroup"]]

    mapping_version = (
        get_most_recent_version(DATA_DIR, args.output_filename, ".xlsx") + 1
    )
    out_path = DATA_DIR / f"{args.output_filename}_v{mapping_version}.xlsx"

    logger.info(f"Writing mapping to {out_path}")
    with pd.ExcelWriter(out_path) as writer:
        df_results.sort_values(["confidence", "score_1"]).to_excel(
            writer, sheet_name="mapping", index=False
        )
        unparseable.to_excel(writer, sheet_name="unparseable_flagged", index=False)

    if args.output_relevant_hs:
        if args.expand_hs_parents:
            logger.info("Expanding matched HS codes with their full ancestor hierarchy")
            relevant_hs = expand_with_ancestors(hs_all, df_results["hs_code_1"])
        else:
            logger.info("Filtering to matched HS codes")
            relevant_hs = hs_all[hs_all["hscode"].isin(df_results["hs_code_1"])]

        hs_version = get_most_recent_version(DATA_DIR, "HS-Codes", ".xlsx") + 1
        hs_out_path = DATA_DIR / f"HS-Codes_v{hs_version}.xlsx"
        logger.info(f"Writing relevant HS codes to {hs_out_path}")
        relevant_hs.to_excel(hs_out_path, index=False)


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
