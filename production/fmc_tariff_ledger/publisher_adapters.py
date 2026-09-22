"""Publisher-specific discovery helpers for FMC tariff locations.

The FMC directory often points thousands of entities at a shared publisher landing
page. Treating that landing page as the carrier tariff would create false evidence.
This module converts known publisher locations into entity-addressable seeds where
possible and identifies carrier-specific links without bypassing authentication.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class SeedURL:
    url: str
    parse_entity_terms: bool
    role: str


COMMON_CORP = {
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation",
    "co", "company", "the", "and", "of", "usa", "us", "international",
    "logistics", "shipping", "freight", "services", "service", "global",
}

FAMILY_HOSTS = {
    "aptariffs": {"aptariffs.com", "www.aptariffs.com", "tariff.aptariffs.com"},
    "ratewave": {"ratewave.com", "www.ratewave.com", "ratewave5.com", "www.ratewave5.com"},
    "dpi": {"dpiusa.com", "www.dpiusa.com", "members.dpiusa.com"},
    "boterates": {"boterates.com", "www.boterates.com"},
    "descartes": {"rates.descartes.com"},
    "dms": {"dmstradeservices.com", "www.dmstradeservices.com"},
    "paramount": {"paramounttariff.com", "www.paramounttariff.com", "search.paramounttariff.com"},
    "tds": {"tariffdatasystems.com", "www.tariffdatasystems.com"},
    "etm": {"etmrates.com", "www.etmrates.com"},
    "firstbay": {"firstbaytariff.com", "www.firstbaytariff.com"},
    "glenrate": {"glenrate.com", "www.glenrate.com"},
    "ace": {"acetariff.com", "www.acetariff.com", "data.acetariff.com"},
    "cargosphere": {"cargosphere.net", "www.cargosphere.net"},
    "blue": {"blue-usa.com", "www.blue-usa.com"},
    "etariff": {"etariff.com", "login.etariff.com", "login2.etariff.com"},
}

AUTH_MARKERS = (
    "secure login",
    "please enter your user id and password",
    "sign in to your environment",
    "user id",
    "password",
)


def host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def family_for(url: str) -> str:
    h = host(url)
    for family, hosts in FAMILY_HOSTS.items():
        if h in hosts or any(h.endswith("." + x.removeprefix("www.")) for x in hosts):
            return family
    return "direct"


def normalize_tokens(value: str) -> set[str]:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\b(?:d/?b/?a|dba)\b", " ", value)
    tokens = re.findall(r"[a-z0-9]{2,}", value)
    return {t for t in tokens if t not in COMMON_CORP and len(t) >= 3}


def entity_match_score(anchor: str, legal_name: str, trade_name: str = "") -> float:
    anchor_tokens = normalize_tokens(anchor)
    if not anchor_tokens:
        return 0.0
    scores = []
    for name in (legal_name, trade_name):
        target = normalize_tokens(name)
        if not target:
            continue
        overlap = len(anchor_tokens & target)
        scores.append(overlap / max(1, min(len(target), len(anchor_tokens))))
    return max(scores, default=0.0)


def seed_urls(
    directory_url: str,
    organization_no: str,
    legal_name: str,
    trade_name: str = "",
) -> list[SeedURL]:
    family = family_for(directory_url)
    seeds = [SeedURL(directory_url, family == "direct", "directory_location")]

    if family == "aptariffs":
        seeds.extend([
            SeedURL(
                "https://tariff.aptariffs.com/member/tariffs"
                f"?locale=en&org_nbr={organization_no}&view=all",
                True,
                "entity_tariff",
            ),
            SeedURL(
                "https://tariff.aptariffs.com/member/tariffs/rules"
                f"?locale=en&tar_code={organization_no}-001&view=all",
                True,
                "entity_rules",
            ),
        ])
    elif family == "ratewave":
        seeds.append(SeedURL("https://www.ratewave.com/rate.html", False, "publisher_index"))
    elif family == "paramount":
        seeds.append(
            SeedURL("https://www.paramounttariff.com/tariff-access", False, "publisher_index")
        )
    elif family == "blue":
        seeds.append(
            SeedURL("https://blue-usa.com/_fmc/lalandia_home.htm", False, "publisher_index")
        )

    # Stable order, no duplicates.
    out: list[SeedURL] = []
    seen: set[str] = set()
    for seed in seeds:
        if seed.url not in seen:
            seen.add(seed.url)
            out.append(seed)
    return out


def auth_or_login_page(text: str, url: str) -> bool:
    low = text.lower()
    if "redirecting..." in low and "/auth/" in low:
        return True
    # Avoid treating ordinary tariff pages that happen to mention passwords as login-only.
    hits = sum(marker in low for marker in AUTH_MARKERS)
    return hits >= 2 or (
        "/login" in urllib.parse.urlsplit(url).path.lower()
        and ("password" in low or "sign in" in low)
    )


def entity_scoped_text(
    text: str,
    organization_no: str,
    legal_name: str,
    trade_name: str = "",
) -> bool:
    low = text.lower()
    if organization_no and organization_no in text:
        return True
    for name in (legal_name, trade_name):
        tokens = normalize_tokens(name)
        if not tokens:
            continue
        hit = sum(t in low for t in tokens)
        if hit >= max(1, min(3, len(tokens))):
            return True
    return False


def allow_cross_publisher_link(
    family: str,
    href: str,
    anchor: str,
    organization_no: str,
    legal_name: str,
    trade_name: str,
) -> tuple[bool, bool]:
    """Return (follow, parse_entity_terms) for a link that failed same-site checks."""
    h = host(href)
    if family == "ratewave" and h.removeprefix("www.") == "ratewave5.com":
        score = entity_match_score(anchor, legal_name, trade_name)
        return (score >= 0.50 or organization_no in anchor, True)
    return (False, False)


def should_parse_entity_terms(
    family: str,
    explicit_parse_flag: bool,
    text: str,
    url: str,
    organization_no: str,
    legal_name: str,
    trade_name: str,
) -> bool:
    if not explicit_parse_flag:
        return False
    if auth_or_login_page(text, url):
        return False
    if family == "direct":
        return True
    return entity_scoped_text(text, organization_no, legal_name, trade_name)
