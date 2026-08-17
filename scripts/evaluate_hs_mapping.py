import argparse
import logging

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from quick_wins.config.hs_codes_config import (
    DATA_DIR,
    EMBEDDING_CACHE_DIR,
    EVAL_SET_PATH,
    HS_TEXT_VERSION,
    QUERY_INSTRUCTION,
)
from quick_wins.tools.hs_codes import (
    import_hs_data,
    add_chapter_column,
    build_hs_encoding_text,
    load_eval_set,
    cached_encode,
    score_eval_set,
    compute_accuracy,
    sweep_thresholds,
)
from quick_wins.tools.hs_codes.matching import model_slug
from quick_wins.tools.hs_codes.text_cleaning import to_encoding_text
from quick_wins.utils.custom_errors import RunningError
from quick_wins.utils.loggers import get_logger
from quick_wins.utils.version_control import get_most_recent_version

NAME = "Evaluate mapping"

SCORE_GRID = [round(x, 2) for x in np.arange(0.35, 0.75, 0.05)]
MARGIN_GRID = [0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]


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
        "-m",
        "--model",
        required=False,
        help="Embedding model to evaluate, default `BAAI/bge-large-en-v1.5`.",
        default="BAAI/bge-large-en-v1.5",
    )
    parser.add_argument(
        "-f",
        "--output_filename",
        required=False,
        help='The file to output the scoring results to, default `Eval scoring`. The ".xlsx" will append automatically.',
        default="Eval scoring",
    )
    return parser.parse_args()


def main(args: argparse.Namespace, logger: logging.Logger) -> None:
    logger.info(f"Loading eval set from {EVAL_SET_PATH}")
    eval_df = load_eval_set(EVAL_SET_PATH)
    n_labeled = int(eval_df["expected_hs_code"].notna().sum())
    logger.info(f"{len(eval_df)} rows loaded ({n_labeled} labeled, {len(eval_df) - n_labeled} abstained)")

    hs_all = import_hs_data()
    hs = hs_all[hs_all["level"] == 6].reset_index(drop=True)
    hs_chaptered = add_chapter_column(hs)

    logger.info(f"Loading embedding model {args.model}")
    model = SentenceTransformer(args.model)

    hs_cache_path = EMBEDDING_CACHE_DIR / f"hs_{model_slug(args.model)}_{HS_TEXT_VERSION}.npy"
    logger.info(f"Encoding/loading {len(hs_chaptered)} HS descriptions (cache: {hs_cache_path})")
    hs_embeddings = cached_encode(
        model,
        build_hs_encoding_text(hs_chaptered),
        hs_cache_path,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    logger.info(f"Encoding {len(eval_df)} eval cargo descriptions")
    query_texts = [QUERY_INSTRUCTION + to_encoding_text(t) for t in eval_df["cargo_text"]]
    eval_embeddings = model.encode(
        query_texts, convert_to_numpy=True, show_progress_bar=True
    )

    logger.info("Scoring eval set")
    scored_df = score_eval_set(eval_df, hs_chaptered, eval_embeddings, hs_embeddings)

    accuracy = compute_accuracy(scored_df)
    logger.info(
        f"[{args.model}] overall (unthresholded top-1) accuracy {accuracy['overall_accuracy']:.0%} "
        f"on {accuracy['n_labeled']} labeled rows ({accuracy['n_abstained']} abstained rows excluded)"
    )

    logger.info(f"Sweeping {len(SCORE_GRID)}x{len(MARGIN_GRID)} score/margin combinations")
    sweep_df = sweep_thresholds(scored_df, SCORE_GRID, MARGIN_GRID)
    scored_sweep = sweep_df[sweep_df["precision"].notna()].sort_values(
        ["precision", "coverage"], ascending=[False, False]
    )

    for floor in (0.9, 0.7):
        candidates = scored_sweep[scored_sweep["precision"] >= floor]
        if len(candidates):
            best = candidates.sort_values("coverage", ascending=False).iloc[0]
            logger.info(
                f"Best coverage at >={floor:.0%} precision: score>={best['score_threshold']}, "
                f"margin>={best['margin_threshold']} -> {best['coverage']:.0%} coverage, "
                f"{best['precision']:.0%} precision, n={best['n_high_confidence']}"
            )
        else:
            logger.warning(f"No threshold combination in the sweep reached {floor:.0%} precision")

    version = get_most_recent_version(DATA_DIR, args.output_filename, ".xlsx") + 1
    out_path = DATA_DIR / f"{args.output_filename}_v{version}.xlsx"
    logger.info(f"Writing scoring results to {out_path}")
    with pd.ExcelWriter(out_path) as writer:
        scored_df.sort_values("cargo_text").to_excel(
            writer, sheet_name="predictions", index=False
        )
        sweep_df.sort_values(["score_threshold", "margin_threshold"]).to_excel(
            writer, sheet_name="threshold_sweep", index=False
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
