from quick_wins.config import DATA_BASE_DIR

DATA_DIR = DATA_BASE_DIR / "hs_code"

BQ_PATH = DATA_DIR / "bq-results-20260807-080738-1786090148990.csv"
HS_PATH = DATA_DIR / "harmonized-system-filtered.csv"
EVAL_SET_PATH = DATA_DIR / "hs_codes_eval_set.csv"

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

# Kept for reference/future ensemble experiments; not currently used in
# production. See scripts/evaluate_hs_mapping.py - a two-model agreement
# gate (bge-m3 + bge-large-en-v1.5) underperformed bge-large-en-v1.5 alone.
EMBEDDING_MODELS = ["BAAI/bge-m3", "BAAI/bge-large-en-v1.5"]

# BGE-family retrieval models expect this prefix on the query (cargo) side
# only - not on the passage (HS description) side.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# A top-1 match is only "high" confidence if it clears this similarity score
# and beats the runner-up by at least MIN_MARGIN. Calibrated against the
# hand-labeled eval set (hs_codes_eval_set.csv) using bge-large-en-v1.5:
# score>=0.65/margin=0.0 gave 71% coverage at 38% precision on 63 labeled
# rows. Coverage was prioritised over precision here because this mapping
# is meant to run against a ~50k-row production database (the eval/sample
# data is only ~6.5k) - maximising the share that gets auto-classified
# matters more than raising precision on a small "high" bucket. Revisit
# once real reviewer feedback on the "needs_review" backlog comes in.
HIGH_CONF_SCORE = 0.65
MIN_MARGIN = 0.0

# Heuristic mapping from commodityGroup to plausible HS chapters (2-digit
# prefixes), used to stop e.g. a "Chemical" cargo matching an unrelated
# chapter. Groups not listed here (e.g. "General cargo") get no restriction -
# they're too broad to guess a chapter from.
GROUP_TO_CHAPTERS = {
    "coal": ["27"],
    "coke": ["27"],
    "crude oil": ["27"],
    "crude": ["27"],
    "refined oil": ["27"],
    "refined oil products": ["27"],
    "mineral oil": ["27"],
    "minerals (liquid cargo)": ["27"],
    "chemical": ["28", "29", "38", "39"],
    "organic liquid products": ["29", "38"],
    "fertilizer (dry cargo)": ["31"],
    "grain": ["10", "11", "12"],
    "ore": ["26"],
    "mineral": ["25", "26"],
    "minerals (dry cargo)": ["25", "26"],
    "cement": ["25"],
    "steel products": ["72", "73"],
}
