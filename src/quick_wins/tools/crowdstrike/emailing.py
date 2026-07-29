import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List

import streamlit as st
import pandas as pd

from quick_wins.tools.crowdstrike import df_to_xlsx_bytes
from quick_wins.utils.html_render import render_template_html


def send_email_with_xlsx_smtp_html(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    mail_from: str,
    mail_to: List[str],
    subject: str,
    body_html: str,
    attachment_bytes: bytes,
    attachment_filename: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = ", ".join(mail_to)
    msg["Subject"] = subject

    # HTML body
    msg.set_content("Please see HTML version of this email.")
    msg.add_alternative(body_html, subtype="html")

    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=attachment_filename,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_username, smtp_password)
        server.send_message(msg)


def email_units(
    *,
    unit_to_df: Dict[str, "pd.DataFrame"],
    unit_to_emails: Dict[str, List[str]],
    file_basename: str,
    email_template_path: Path,
) -> None:
    smtp_host = st.secrets["SMTP_HOST"]
    smtp_port = int(st.secrets["SMTP_PORT"])
    smtp_username = st.secrets["SMTP_USERNAME"]
    smtp_password = st.secrets["SMTP_PASSWORD"]
    mail_from = st.secrets["MAIL_FROM"]
    sender_name = st.secrets.get("SENDER_NAME", "Automated Reports")

    for unit_name, df_unit in unit_to_df.items():
        emails = unit_to_emails.get(unit_name, [])
        if not emails:
            continue

        attachment_bytes = df_to_xlsx_bytes(df_unit, sheet_name="Data")
        filename = f"{file_basename}_{unit_name}.xlsx".replace("/", "-")

        subject = f"Weekly report - {unit_name}"
        body_html = render_template_html(
            email_template_path,
            {
                "unit_name": unit_name,
                "sender_name": sender_name,
            },
        )

        send_email_with_xlsx_smtp_html(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            mail_from=mail_from,
            mail_to=emails,
            subject=subject,
            body_html=body_html,
            attachment_bytes=attachment_bytes,
            attachment_filename=filename,
        )
