from typing import List

from quick_wins.config import DATA_BASE_DIR

DATA_DIR = DATA_BASE_DIR / "crowdstrike"

# Per-upload Critical/High vulnerability counts aggregated by unit (country),
# appended to on every zip upload so a trendline can be plotted over time.
HISTORY_PATH = DATA_DIR / "vulnerability_history.csv"

COLS_TO_DROP: List[str] = [
    "LocalIP",
    "OU",
    "SiteName",
    "Count",
    "Unknown",
    "Unknown",
    "GroupNames",
    "Tags",
    "HostID",
    "Platform",
    "ExPRT Critical",
    "ExPRT High",
    "ExPRT Medium",
    "ExPRT Low",
    "ExPRT Unknown",
    "Asset Criticality",
    "Asset Roles",
    "Internet exposure",
    "Managed By",
    "Data Providers",
    "Third-party Asset IDs",
    "CID",
    "Customer",
    "Recommendation Type",
    "Patch Publication Date",
    "Instance state",
]
