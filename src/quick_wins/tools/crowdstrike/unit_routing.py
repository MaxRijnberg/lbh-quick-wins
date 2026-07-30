from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Sequence, Tuple, TypedDict


class EmailRecipient(TypedDict):
    email: str
    name: str
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class UnitConfig:
    name: str
    aliases: List[str]
    domains: List[str]
    emails: List[EmailRecipient]
    abbreviation: str  # required (e.g., "ZA", "NL", "CN")


def load_unit_config(config_path: Path) -> Dict[str, UnitConfig]:
    with open(config_path, "r", encoding="utf-8") as f:
        raw: Dict[str, Dict[str, object]] = json.load(f)

    out: Dict[str, UnitConfig] = {}
    for unit_name, cfg in raw.items():
        abbr = str(cfg.get("abbreviation", "")).strip()
        if not abbr:
            raise ValueError(f"Missing required 'abbreviation' for unit '{unit_name}'")

        out[unit_name] = UnitConfig(
            name=unit_name,
            aliases=list(cfg.get("aliases", [])),  # type: ignore[arg-type]
            domains=list(cfg.get("domains", [])),  # type: ignore[arg-type]
            emails=list(cfg.get("emails", [])),  # type: ignore[arg-type]
            abbreviation=abbr,
        )
    return out


def _normalize_tag(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()


def _compile_alias_regex(aliases: Sequence[str]) -> List[Pattern[str]]:
    patterns: List[Pattern[str]] = []
    for alias in aliases:
        alias_clean = (alias or "").strip()
        if not alias_clean:
            continue
        alias_norm = _normalize_tag(alias_clean)
        patterns.append(re.compile(re.escape(alias_norm), flags=re.IGNORECASE))
    return patterns


def build_tag_alias_matchers(
    unit_configs: Dict[str, UnitConfig],
) -> List[Tuple[str, List[Pattern[str]]]]:
    matchers: List[Tuple[str, List[Pattern[str]]]] = []
    for unit_name, uc in unit_configs.items():
        matchers.append((unit_name, _compile_alias_regex(uc.aliases)))
    return matchers


def match_unit_from_tags(
    tags_value: Optional[str],
    alias_matchers: List[Tuple[str, List[Pattern[str]]]],
) -> Optional[str]:
    if tags_value is None or (isinstance(tags_value, float) and pd.isna(tags_value)):
        return None

    tokens = [t.strip() for t in str(tags_value).split(",") if t.strip()]
    if not tokens:
        return None

    tokens_norm = [_normalize_tag(t) for t in tokens]

    # Return first unit match (same behavior as before)
    for unit_name, patterns in alias_matchers:
        for token_norm in tokens_norm:
            for pat in patterns:
                if pat.search(token_norm):
                    return unit_name
    return None


def extract_domain_suffix(machine_domain: Optional[str]) -> Optional[str]:
    if machine_domain is None or (
        isinstance(machine_domain, float) and pd.isna(machine_domain)
    ):
        return None
    return str(machine_domain).strip().lower()


def match_unit_from_domains(
    machine_domain: Optional[str],
    unit_configs: Dict[str, UnitConfig],
) -> Optional[str]:
    domain_str = extract_domain_suffix(machine_domain)
    if not domain_str:
        return None

    best_unit: Optional[str] = None
    best_len: int = -1

    for unit_name, uc in unit_configs.items():
        for suffix in uc.domains:
            suf = (suffix or "").strip().lower()
            if not suf:
                continue
            if domain_str.endswith(suf) and len(suf) > best_len:
                best_len = len(suf)
                best_unit = unit_name
    return best_unit


def _normalize_abbreviation(abbreviation: str) -> str:
    # "first two letters" implies case-insensitive, and we treat it as literal letters
    return re.sub(r"\s+", "", abbreviation.strip()).upper()


def match_unit_from_hostname(
    hostname: Optional[str],
    unit_configs: Dict[str, UnitConfig],
) -> Optional[str]:
    """
    Uses the first two letters of Hostname to match unit.abbreviation.
    Example: Hostname starts with "ZA..." => unit with abbreviation "ZA".
    """
    if hostname is None or (isinstance(hostname, float) and pd.isna(hostname)):
        return None

    host = str(hostname).strip()
    if len(host) < 2:
        return None

    prefix = host[:2].upper()

    # Build quick map each call is ok for small configs; if large, cache.
    for unit_name, uc in unit_configs.items():
        if _normalize_abbreviation(uc.abbreviation) == prefix:
            return unit_name
    return None


def assign_unit_column(
    df: pd.DataFrame,
    unit_configs: Dict[str, UnitConfig],
    tags_col: str = "Tags",
    domain_col: str = "MachineDomain",
    hostname_col: str = "Hostname",
) -> pd.DataFrame:
    alias_matchers = build_tag_alias_matchers(unit_configs)

    def row_unit(row: pd.Series) -> Optional[str]:
        u = match_unit_from_tags(row.get(tags_col), alias_matchers)
        if u is not None:
            return u

        u = match_unit_from_domains(row.get(domain_col), unit_configs)
        if u is not None:
            return u

        # Step 3: Hostname abbreviation (fallback)
        return match_unit_from_hostname(row.get(hostname_col), unit_configs)

    df2 = df.copy()
    df2["unit"] = df2.apply(row_unit, axis=1)
    return df2
