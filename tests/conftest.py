from pathlib import Path

import pandas as pd
import pytest

CONFIG_DIR = Path(__file__).resolve().parent.parent / "src" / "quick_wins" / "config"


@pytest.fixture
def email_template_path() -> Path:
    return CONFIG_DIR / "crowdstrike_email.html"


@pytest.fixture
def sample_vulnerabilities_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Hostname": ["ZA-TEST-01", "NL-TEST-02"],
            "Tags": ["LBH South Africa", "LBH The Netherlands"],
            "MachineDomain": ["test.co.za", "test.local"],
            "Severity": ["High", "Medium"],
            "CVE": ["CVE-2026-0001", "CVE-2026-0002"],
        }
    )
