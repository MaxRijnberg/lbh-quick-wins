from quick_wins.config import DATA_BASE_DIR

DATA_DIR = DATA_BASE_DIR / "hs_code"

BQ_PATH = DATA_DIR / "bq-results-20260807-080738-1786090148990.csv"
BQ_VC_PATH = DATA_DIR / "bq-results-20260813-081157-1786608752807.csv"
HS_PATH = DATA_DIR / "harmonized-system-filtered.csv"
EVAL_SET_PATH = DATA_DIR / "hs_codes_eval_set.csv"

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

# The HS-description side embeddings are the same ~3.6k vectors regardless
# of which cargo batch is being matched, and re-encoding them (~11 min for
# BAAI/bge-large-en-v1.5 on CPU) every run was slowing down iteration -
# cache them to disk per model, keyed by model name.
EMBEDDING_CACHE_DIR = DATA_DIR / "embedding_cache"

# Bump whenever the text fed into the HS-side embeddings changes (e.g. a new
# entry in HS_DESCRIPTION_SYNONYMS) - the cache above is keyed by filename
# only, so without this an edit to the synonym text would silently keep
# serving stale embeddings computed from the old description text.
HS_TEXT_VERSION = "v2"

# BGE-family retrieval models expect this prefix on the query (cargo) side
# only - not on the passage (HS description) side.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# A top-1 match is only "high" confidence if it clears this similarity score
# AND beats the runner-up by at least MIN_MARGIN. Score alone can't tell a
# clear winner from a coin-flip tie - e.g. "Coal" scored anthracite and
# bituminous within 0.0003 of each other, both above HIGH_CONF_SCORE, with
# nothing in the source text to actually distinguish the two. HIGH_CONF_SCORE
# was calibrated against the hand-labeled eval set (hs_codes_eval_set.csv)
# using bge-large-en-v1.5: score>=0.65 gave ~71% coverage at ~38% precision on
# the labeled rows (this was before MIN_MARGIN was reintroduced - due for
# re-calibration together with it). Coverage was prioritised over precision
# because this mapping runs against a ~50k-row production database (the eval
# sample is only ~6.5k) - maximising the auto-classified share matters more
# than raising precision on a small "high" bucket. Revisit both once real
# reviewer feedback on the "needs_review" backlog comes in.
HIGH_CONF_SCORE = 0.65
MIN_MARGIN = 0.02

# Common shipping/commodity trade abbreviations that carry no semantic
# content for an embedding model on their own (e.g. "C3 LPG" matched
# "Helium-3" - pure token coincidence, not meaning). Expanded to their full
# form before encoding. Deliberately excludes ambiguous placeholders like
# "TBC"/"GUCD" that aren't actually commodities - inventing an expansion for
# those would be worse than leaving them unparseable.
ABBREVIATIONS = {
    "LNG": "liquefied natural gas",
    "LPG": "liquefied petroleum gas",
    "ULSD": "ultra low sulphur diesel",
    "AGO": "atmospheric gasoil",
    "MGO": "marine gas oil",
    "HFO": "heavy fuel oil",
    "IFO": "intermediate fuel oil",
    "VLSFO": "very low sulphur fuel oil",
    "HSFO": "high sulphur fuel oil",
    "MOP": "muriate of potash",
    "SOP": "sulphate of potash",
    "UAN": "urea ammonium nitrate",
    "DAP": "diammonium phosphate",
    "MAP": "monoammonium phosphate",
    "NPK": "nitrogen phosphorus potassium fertilizer",
    "PCI": "pulverised coal injection",
    "ROM": "run of mine",
    "CPO": "crude palm oil",
    "RBD": "refined bleached deodorized palm oil",
    "PKO": "palm kernel oil",
    "EBOB": "gasoline blendstock",
    "WTI": "west texas intermediate crude oil",
    "C3": "propane",
    "C4": "butane",
    "RVP": "reid vapor pressure",
    "DDGS": "distillers dried grains with solubles",
    "YSB": "soybeans",
    "GBFS": "granulated blast furnace slag",
    "HVO": "hydrotreated vegetable oil",
    "MFO": "marine fuel oil",
    "D2": "diesel oil",
    "SN150": "solvent naphtha 150",
    "RMG380": "residual marine gas oil 380 cst",
    "MTBE": "methyl tert-butyl ether",
    "EOL": "end of life",
    "NAOH": "sodium hydroxide",
    # Additions in the same vein - same reasoning as above, not directly
    # observed failing in the eval set but common enough in bulk shipping
    # that they're likely to show up at full (50k-row) scale.
    "VGO": "vacuum gas oil",
    "HSD": "high speed diesel",
    "MOGAS": "motor gasoline",
    "ATF": "aviation turbine fuel",
    "RBOB": "reformulated blendstock for oxygenate blending gasoline",
    "CBOB": "conventional blendstock for oxygenate blending gasoline",
    "FAME": "fatty acid methyl ester biodiesel",
    "UCO": "used cooking oil",
    "POME": "palm oil mill effluent",
    "DRI": "direct reduced iron",
    "HBI": "hot briquetted iron",
    "TSP": "triple superphosphate",
    "SSP": "single superphosphate",
    "HDPE": "high density polyethylene",
    "LDPE": "low density polyethylene",
    "PVC": "polyvinyl chloride",
    "HMS": "heavy melting scrap",
    "HRC": "hot rolled coil steel",
    "CRC": "cold rolled coil steel",
    # Mined from the actual bq sample (token frequency count over `name`) -
    # these appear 11-45 times each in the ~6.5k row sample, so are worth
    # real confidence in, unlike guessing at terms never observed. Excludes
    # tokens that turned out to be plain English words the ALL-CAPS source
    # data just made look like abbreviations (BULK, OIL, COAL, STEEL, etc.),
    # and a few (EVR, VT2/VT3, MLV, HSSR, IP) that are likely supplier/mine-
    # specific codes with no confidently-known public meaning - guessing
    # wrong there would be worse than leaving them as-is.
    "PPM": "parts per million",
    "RON": "research octane number",
    "HEFA": "hydroprocessed esters and fatty acids",
    "SPK": "synthetic paraffinic kerosene",
    "RMG": "residual marine fuel",
    "CWRS": "canada western red spring wheat",
    "UCOME": "used cooking oil methyl ester",
    # No blend % in the expansion - the number would otherwise get stripped
    # by remove_bare_numbers downstream, and the % doesn't change the 6-digit
    # code anyway (both are still just gasoline, HS 271012). "gasoline"
    # deliberately comes first in the expansion (not "ethanol blend
    # gasoline") - KEYWORD_HS_OVERRIDES matches leftmost-first, and since
    # "ethanol" is also a keyword there (-> 220720), the old word order let
    # E5/E10 rows get misclassified as pure ethanol instead of the
    # ethanol-blended gasoline they actually are.
    "E5": "gasoline ethanol blend",
    "E10": "gasoline ethanol blend",
    "SRFO": "straight run fuel oil",
    "UKBOB": "uk blendstock for oxygenate blending gasoline",
    "EUROBOB": "gasoline blendstock",
    "GGBFS": "ground granulated blast furnace slag",
    "DMA": "distillate marine fuel",
    "CST": "centistokes",
    "OXY": "oxygenate",
    # Added after auditing the highest-value_count rows in a full mapping
    # run: bare shorthand that scored well below its true HS description
    # because the description-side text never uses the trade term itself
    # (see HS_DESCRIPTION_SYNONYMS below for the matching fix on that side).
    "PETCOKE": "petroleum coke",
    "SBM": "soybean meal",
    "METCOKE": "metallurgical coke",
}

# Mineral/product names that are already full, real words (not acronyms) but
# whose bare text embeds closer to an unrelated HS description than to the
# one that actually names them - e.g. "Bauxite" alone scored higher against
# "Gypsum; anhydrite" (252010) than against "Aluminium ores and concentrates"
# (260600), confirmed both by direct inspection and by the hand-labeled eval
# set (hs_codes_eval_set.csv note: "semantically unrelated minerals, no
# obvious lexical link... still a top-20-volume miss"). Unlike ABBREVIATIONS
# above these are appended as a clarifying suffix rather than substituted,
# since the original term still carries real information (the mineral/brand
# identity) worth keeping for a human reviewer. Only added where the
# name-to-commodity link is unambiguous and independently verifiable
# (mineralogy references for ores, published product data sheets for named
# commercial products) - a wrong guess here is worse than leaving the row to
# fall through to manual review.
#
# "TACORA PREMIUM CONCENTRATE" is keyed as the full phrase rather than the
# bare brand name "TACORA" - the same dataset also has "Tacora Ferro
# Manganese" rows, which the pipeline already classifies correctly as
# manganese ore; a bare-word "Tacora -> iron ore" alias would have corrupted
# those.
COMMODITY_ALIASES = {
    "BAUXITE": "aluminium ore",
    "TACORA PREMIUM CONCENTRATE": "iron ore concentrate",
    # Adaro's trademarked low-rank coal product - "Envirocoal" doesn't
    # tokenize as containing the word "coal" the way e.g. "Thermal Coal"
    # does, so it was matching waste petroleum oils (271099) instead of any
    # coal code despite commodityGroup already being "Coal".
    "ENVIROCOAL": "coal",
    "ILMENITE": "titanium ore",
    "MAGNETITE": "iron ore",
    # Both spellings observed in the data ("Tyres"/"Tires"). Bare "tyres"
    # alone is too broad to alias (could mean actual retreaded/new tyres),
    # but "shredded tyres/tires" specifically means rubber scrap for
    # reclaiming or fuel, not a tyre product - was matching "Retreaded
    # tyres; of a kind used on aircraft" (401213), which is nonsensical for
    # bulk shipping cargo.
    "SHREDDED TYRES": "rubber scrap",
    "SHREDDED TIRES": "rubber scrap",
}

# HS 6-digit descriptions are written in formal customs-legal language that
# often shares no vocabulary at all with how a commodity is actually named in
# trade - e.g. "Oils and products of the distillation of high temperature
# coal tar; naphthalene" (270740) is a specific coal-tar chemical byproduct,
# but its text was winning the similarity race against Gasoline, Fuel Oil,
# Jet A1, Diesel, VGO and Gas Oil (all of which actually belong under 271012
# "light oils" or 271019 "not light oils" - codes that legally describe them
# but never use those words). Confirmed via the hand-labeled eval set: a
# "high confidence" Gasoline row was matched to 270740 outright (note:
# "the chapter-2707-vs-2710 confusion flagged during earlier reranking
# experiments, now confirmed hitting a top-20-volume commodity while marked
# 'high' confidence"). Rather than patch this per cargo description (which
# doesn't scale and misses future variants), the fix is on the HS reference
# side: append plain-English trade synonyms to the handful of description
# strings identified as false attractors, so the embedding for the *correct*
# code also picks up the vocabulary a real shipping description would use.
# Keyed by 6-digit HS code (zero-padded).
HS_DESCRIPTION_SYNONYMS = {
    "271012": "gasoline petrol motor spirit petroleum naphtha light naphtha",
    "271019": "diesel gas oil gasoil kerosene fuel oil heavy fuel oil jet fuel vacuum gas oil",
    "270900": "crude oil crude petroleum",
    "270112": "thermal coal steam coal coking coal metallurgical coal",
    "250100": "rock salt sea salt sodium chloride",
    "230330": "distillers dried grains with solubles ddgs",
    "261400": "ilmenite rutile titanium ore",
    "270400": "metallurgical coke foundry coke metcoke",
    "400400": "shredded tyres shredded tires tyre scrap tire scrap",
}

# Cargo "names" that don't describe an actual commodity - shipment-admin
# placeholders that happen to embed as a false-positive "high confidence"
# match against an arbitrary HS code purely because there's no real
# commodity signal in the text for the embedding to anchor on (e.g.
# "multiple parcel's" scored 0.65 against "Plastics; boxes, cases, crates
# and similar articles for the conveyance or packing of goods", 392390).
# Forced to needs_review regardless of score - there's no substitute for a
# human actually reading the shipment to know what's inside. Matched after
# normalizing to lowercase alphanumerics-and-spaces only, so punctuation/case
# variants ("General Cargo", "GENERAL CARGO") all hit the same entry.
NON_SPECIFIC_CARGO_TERMS = {
    "general cargo",
    "project cargo",
    "multiple parcels",
    "bulk",
    "various",
}

# Deterministic term -> 6-digit HS code overrides, checked before any
# embedding similarity is computed. HS_DESCRIPTION_SYNONYMS above (appending
# plain-English trade terms to the HS description text) measurably improved
# overall eval accuracy, but for this specific cluster it wasn't enough:
# direct testing (both append-style and full-replacement encoding text)
# confirmed Gasoline/Diesel/Fuel Oil/Jet Fuel/Vacuum Gas Oil still lost to
# "Oils and products of the distillation of high temperature coal tar"
# (270740 and its siblings 270710/270720/270791/270799) regardless of
# wording - that cluster has a very strong, wording-independent pull in this
# embedding model for anything phrased like "oils ... products ... refined".
# Rather than keep chasing it with description text, these terms are
# resolved by direct rule instead: unambiguous in a bulk-shipping context
# (no other real-world meaning here), matched word-boundary/case-insensitive
# against the fully cleaned cargo text (so abbreviation expansions like
# HSD -> "high speed diesel" or VGO -> "vacuum gas oil" already feed into
# this automatically). "Coking coal"/"steam coal" are included for the same
# reason - "coking" shares a root with "coke", which reliably pulled those
# rows into the coke code (270400) instead of raw bituminous coal (270112)
# even after HS_DESCRIPTION_SYNONYMS. "Crude oil" and "salt" are the full
# 2-word/1-word phrase, not bare substrings, specifically to avoid
# misclassifying unrelated products that happen to contain the word (e.g.
# "Crude Palm Oil" is vegetable oil, chapter 15, not petroleum crude -
# confirmed via the hand-labeled eval set; "salt" was checked against every
# occurrence in the full mapping run and found to always mean table/rock
# salt in this dataset, never a chemical compound name). "Naphtha" is the
# same coal-tar-cluster problem as gasoline/diesel above. "Wheat" is a
# different bug entirely - bare "Wheat" was matching a processed-product
# code (1103 "cereal groats and meal") instead of any raw-grain code in
# chapter 10, for reasons unrelated to the coal-tar cluster - included here
# because embedding fixes didn't move it either.
KEYWORD_HS_OVERRIDES = {
    "GASOLINE": "271012",
    "PETROL": "271012",
    "MOTOR SPIRIT": "271012",
    "DIESEL": "271019",
    "GAS OIL": "271019",
    "GASOIL": "271019",
    "KEROSENE": "271019",
    "FUEL OIL": "271019",
    "JET FUEL": "271019",
    "JET A1": "271019",
    "JET A-1": "271019",
    "CRUDE OIL": "270900",
    "COKING COAL": "270112",
    "STEAM COAL": "270112",
    "THERMAL COAL": "270112",
    "SALT": "250100",
    "NAPHTHA": "271012",
    # Neodene (INEOS/Shell linear alpha olefins) is unambiguous but the
    # embedding alias below wasn't enough on its own - it moved the match
    # off the wrong chapter (3824 "chemical products n.e.c.") but onto the
    # wrong *sub*-family within the right chapter (2902 cyclic hydrocarbons
    # instead of 2901 acyclic/unsaturated, where linear alpha olefins
    # actually belong) - same "close but still wrong" pattern as the
    # coal-tar cluster, so resolved the same way.
    "NEODENE": "290129",
    # "DURUM WHEAT" is listed before the bare "WHEAT" fallback (and wins,
    # since KEYWORD_HS_OVERRIDES is matched longest-phrase-first) so
    # genuine durum wheat rows ("Better Amber Durum Wheat", confirmed
    # present in the full mapping run) get the durum code instead of being
    # forced onto the generic/non-durum one.
    "DURUM WHEAT": "100119",
    "WHEAT": "100199",
    "SOYBEANS": "120190",
    "SOYABEANS": "120190",
    "SOYBEAN": "120190",
    "SOYABEAN": "120190",
    "SOYA BEANS": "120190",
    "SOY BEANS": "120190",
    "CORN": "100590",
    "MAIZE": "100590",
    "BARLEY": "100390",
    "ETHANOL": "220720",
    "METHANOL": "290511",
    "SULPHURIC ACID": "280700",
    "CAUSTIC SODA SOLUTION": "281512",
    "LIQUID CAUSTIC SODA": "281512",
    "CAUSTIC SODA": "281511",
}

# "Distillers dried grains with solubles" (DDGS, after abbreviation
# expansion) gets matched with priority - ahead of the bare grain overrides
# above - because it can appear anywhere in text that ALSO contains "corn"/
# "maize"/"barley" (e.g. "Corn Distiller Grain Meal (DDGS)", "Maize DDGS
# Proticorn in pellets") without being adjacent to it, so the normal
# leftmost-match-wins order isn't reliable here; these rows already
# classify correctly via the embedding match alone (DDGS is chapter 23, a
# clearly different product from the raw grain), so this only guards
# against the new CORN/MAIZE/BARLEY overrides below accidentally breaking
# them.
DDGS_HS_CODE = "230330"

# Modifier + commodity combinations that must NOT be swept up by the bare
# SOYBEAN*/CORN/BARLEY/ETHANOL overrides above, because they name a
# genuinely different product with its own (not reviewed/confirmed here) HS
# code, or because the source text already specifies "seed" and the bare
# override (which targets the non-seed 6-digit variant) would wrongly
# overwrite an already-correct seed-code match:
#   - soybean/soya bean oil, methyl esters, hulls and cake are all
#     processing byproducts or derived products, not whole beans.
#   - "Soybean Seeds"/"Yellow Soybean Seeds" was already correctly matching
#     the seed code (120110) via the embedding alone; forcing it to the
#     bare-override's non-seed code (120190) would have been a regression.
#   - corn oil and corn gluten are processed byproducts, not raw corn.
#   - "barley husk" is a milling byproduct (husk/bran), not the grain -
#     confirmed a real miss: "Barley Husk Pellets" was already correctly
#     landing on "Cereal pellets" (110320) via the embedding alone before
#     this fix existed, and the bare BARLEY override was overwriting that
#     with the raw-grain code.
#   - anhydrous/hydrous/(un)denatured/bio ethanol each carry their own
#     denaturing-status distinction the plain "Ethanol" correction
#     (-> 220720, denatured of any strength) doesn't necessarily apply to.
# Matched anywhere in the cargo text (not just at the leftmost position) -
# if found, ALL keyword overrides are skipped for that row and it falls
# through to the embedding match instead, same as before this fix existed.
KEYWORD_OVERRIDE_EXCLUSION_PATTERN = (
    r"\b(?:soybean|soya\s+bean|soyabean)s?\s+(?:oil|meals?|methyl\s+esters?|hulls?|cake)\b"
    r"|\b(?:corn|maize|barley|soybean|soya\s+bean|soyabean)s?\s+seeds?\b"
    r"|\bcorn\s+(?:oil|gluten)\b"
    r"|\bbarley\s+husk\b"
    r"|\b(?:anhydrous|hydrous|denatured|undenatured|bio)\s+(?:fuel\s+)?ethanol\b"
)

# Packaging/logistics phrases that describe how cargo is packed, not what it
# is - noise for a semantic matcher trying to identify the underlying
# commodity (e.g. "Bagged Rice" and "Rice in Bulk" are the same HS code).
# Stripped out entirely rather than expanded.
FILLER_PHRASES = [
    "in bulk",
    "loose bulk",
    "in bigbag",
    "in big bag",
    "bigbag",
    "big bag",
    "in bags",
    "in bag",
    "bagged",
    "in drums",
    "in containers",
    # Also mined from the bq sample - packaging descriptors beyond bulk/bag
    # that "in bulk"/"bagged" above don't cover.
    "sling bag",
    "sling bags",
    "bags",
    "bag",
]

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
    # "72" included because DRI/HBI (Direct Reduced Iron / Hot Briquetted
    # Iron) commonly ship under an "Ore" commodityGroup label despite being
    # a processed steel-industry product (HS chapter 72), not ore (26) -
    # restricting to 26 only was silently guaranteeing those rows wrong.
    "ore": ["26", "72"],
    # Same DRI/HBI reasoning as "ore" above - these generic dry-bulk-mineral
    # groups can also carry processed steel-industry cargo. "27" added for
    # the same kind of reason: petroleum coke ("Petcoke") is routinely
    # tagged under these generic mineral groups too, and without it the
    # restriction was actively blocking the correct chapter-27 code (coke
    # rows here were landing on "Barium carbonate" and similar chapter-25
    # nonsense) even after the PETCOKE abbreviation expansion above.
    "mineral": ["25", "26", "27", "72"],
    "minerals (dry cargo)": ["25", "26", "27", "72"],
    "cement": ["25"],
    "steel products": ["72", "73"],
}
