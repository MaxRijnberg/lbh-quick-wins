"""
Sends real emails through the configured SMTP relay so the rendered output
(subject, HTML body, XLSX attachment) can be checked by eye in an inbox.

These hit real SMTP infrastructure, so they're excluded from the default
`pytest` run (see the `integration` marker in pyproject.toml). Run them
explicitly with:

    pytest -m integration

Before running, replace TEST_RECIPIENT below with an inbox you can check.
Requires .streamlit/secrets.toml to hold working SMTP credentials.
"""

import pytest
import streamlit as st
import pandas as pd

from typing import List, TypedDict, Dict
from pathlib import Path

from quick_wins.tools.crowdstrike import df_to_xlsx_bytes, email_units
from quick_wins.tools.crowdstrike.unit_routing import EmailRecipient
from quick_wins.tools.crowdstrike.emailing import send_email_with_xlsx_smtp_html
from quick_wins.utils.html_render import render_template_html

TEST_RECIPIENT: str = st.secrets["TEST_RECIPIENT"]

pytestmark = pytest.mark.integration


class SMTPConfig(TypedDict):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    mail_from: str


def _smtp_config() -> SMTPConfig:
    returnval: SMTPConfig = {
        "smtp_host": st.secrets["SMTP_HOST"],
        "smtp_port": int(st.secrets["SMTP_PORT"]),
        "smtp_username": st.secrets["SMTP_USERNAME"],
        "smtp_password": st.secrets["SMTP_PASSWORD"],
        "mail_from": st.secrets["MAIL_FROM"],
    }
    return returnval


def test_send_email_with_xlsx_smtp_html_smoke(
    sample_vulnerabilities_df: pd.DataFrame, email_template_path: Path
) -> None:
    """Sends one email with an XLSX attachment directly, bypassing unit routing."""
    attachment_bytes = df_to_xlsx_bytes(sample_vulnerabilities_df, sheet_name="Data")
    body_html = render_template_html(
        email_template_path,
        {
            "name": "Test Recipient",
            "unit_name": "TEST",
            "file_name": "test_report.xlsx",
            "row_count": len(sample_vulnerabilities_df),
            "sender_name": "Quick Wins Test Suite",
        },
    )

    send_email_with_xlsx_smtp_html(
        **_smtp_config(),
        mail_to=[TEST_RECIPIENT],
        subject="[TEST] Crowdstrike report - smoke test",
        body_html=body_html,
        attachment_bytes=attachment_bytes,
        attachment_filename="test_report.xlsx",
    )


def test_email_units_end_to_end(
    sample_vulnerabilities_df: pd.DataFrame, email_template_path: Path
) -> None:
    """Runs the same email_units() pipeline the Streamlit page calls, routed to the test address."""
    unit_to_df = {"TEST_UNIT": sample_vulnerabilities_df}
    unit_to_emails: Dict[str, List[EmailRecipient]] = {
        "TEST_UNIT": [{"email": TEST_RECIPIENT, "name": "Test Recipient"}]
    }

    email_units(
        unit_to_df=unit_to_df,
        unit_to_emails=unit_to_emails,
        file_basename="CrowdstrikeVulnerabilities_test",
        email_template_path=email_template_path,
    )
