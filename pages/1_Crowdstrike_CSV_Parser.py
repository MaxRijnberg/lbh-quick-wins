import os

import streamlit as st

from pathlib import Path

from quick_wins.tools.crowdstrike import (
    read_first_csv_from_zip,
    load_unit_config,
    assign_unit_column,
    email_units,
    stacked_risk_by_unit,
    vulnerability_trendline,
    aggregate_critical_high_by_unit,
    append_to_history,
    load_history,
)

CONFIG_DIR = (
    Path(os.path.dirname(__file__)).resolve().parent / "src" / "quick_wins" / "config"
)

CONFIG_PATH = CONFIG_DIR / "crowdstrike_config.json"


EMAIL_TEMPLATE_PATH = CONFIG_DIR / "crowdstrike_email.html"


def _load_unit_config_cached():
    return load_unit_config(CONFIG_PATH)


st.set_page_config(page_title="Crowdstrike Vulnerabilities CSV", layout="wide")

st.title("Automatic emailing of Crowdstrike Vulnerabilities")

# --- Trendline of Critical + High vulnerabilities per unit over time ---
# Independent of the uploader below - viewable any time from prior history.
if "show_crowdstrike_trendline" not in st.session_state:
    st.session_state["show_crowdstrike_trendline"] = False

if st.toggle("View vulnerability trendline (per country)"):
    st.session_state["show_crowdstrike_trendline"] = True

if st.session_state["show_crowdstrike_trendline"]:
    trend_history = load_history()
    available_units = sorted(trend_history["unit"].unique()) if not trend_history.empty else []
    selected_units = st.multiselect(
        "Countries to show",
        options=available_units,
        default=available_units,
    )
    vulnerability_trendline(trend_history, selected_units=selected_units)

uploaded = st.file_uploader("Upload CrowdstrikeVulnerabilities.csv.zip", type=["zip"])

if uploaded is None:
    st.stop()

# Load and route
df, csv_name = read_first_csv_from_zip(uploaded)
st.write(f"Loaded CSV: {csv_name}")
st.write(f"Rows in CSV: {len(df)}")

unit_configs = _load_unit_config_cached()
df = assign_unit_column(df, unit_configs, tags_col="Tags", domain_col="MachineDomain")

df_inferred = df[df["unit"].notna()].copy()
df_unknown = df[df["unit"].isna()].copy()

st.write(f"Rows inferred to units: {len(df_inferred)}")
st.write(f"Rows with no country/unit inferred: {len(df_unknown)}")

# Optional quick overview chart
if len(df_inferred) > 0:
    stacked_risk_by_unit(df_inferred)

# --- Append aggregated Critical/High counts per unit to history CSV ---
# Streamlit reruns this whole script on every widget interaction, so guard
# on the upload's file_id to avoid re-appending the same data on every rerun
# (e.g. toggling "Preview errors" or clicking the email/trendline buttons).
if len(df_inferred) > 0:
    if st.session_state.get("crowdstrike_history_file_id") != uploaded.file_id:
        history_agg = aggregate_critical_high_by_unit(df_inferred)
        append_to_history(history_agg)
        st.session_state["crowdstrike_history_file_id"] = uploaded.file_id
        st.success(f"Appended {len(history_agg)} unit rows to vulnerability history.")
    else:
        st.caption("This upload was already recorded in the vulnerability history.")

# --- Preview unknown first (as requested) ---
st.subheader("Preview: rows with NO unit inferred (errors)")
if st.toggle("Preview errors"):
    st.write(df_unknown)

# --- Email button (one XLSX per unit, full table) ---
st.subheader("Emailing")
unit_names = sorted(df_inferred["unit"].unique().tolist())

if st.button("Email XLSX to managers (per unit)"):
    if len(df_inferred) == 0:
        st.error("No inferred rows to email.")
        st.stop()

    # Prepare data for email_units()
    unit_to_df = {u: df_inferred[df_inferred["unit"] == u].copy() for u in unit_names}
    unit_to_emails = {
        u: unit_configs[u]["emails"] for u in unit_names if u in unit_configs
    }

    file_basename = os.path.splitext(os.path.basename(csv_name))[0]

    with st.spinner("Sending emails..."):
        email_units(
            unit_to_df=unit_to_df,
            unit_to_emails=unit_to_emails,
            file_basename=file_basename,
            email_template_path=EMAIL_TEMPLATE_PATH,
        )

    st.success("Emails sent.")
