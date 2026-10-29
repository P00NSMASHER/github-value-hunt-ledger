"""Offline, curated evidence comparison; not a predictive procurement engine."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ISSUER_HOSTS = {
    "guam-waterworks-authority": {"guamwaterworks.org", "www.guamwaterworks.org"},
    "navajo-tribal-utility-authority": {"ntua.com", "www.ntua.com"},
}


def trusted(url, hosts):
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in hosts and not parsed.username and not parsed.password
    except (TypeError, ValueError):
        return False


def evaluate(signal, bid):
    if signal.get("agency") != bid.get("agency"):
        return ("NO_MATCH", "agency", None)
    if signal.get("facility") != bid.get("facility"):
        return ("NO_MATCH", "facility", None)
    if signal.get("scope") != bid.get("scope"):
        return ("REVIEW", "scope_not_exact", None)
    if not trusted(signal.get("url"), {"epa.gov", "www.epa.gov"}):
        return ("REVIEW", "signal_source", None)
    if not trusted(bid.get("url"), ISSUER_HOSTS.get(bid.get("agency"), set())):
        return ("REVIEW", "bid_source", None)
    try:
        start = date.fromisoformat(signal["date"])
        end = date.fromisoformat(bid["issue_date"])
    except (KeyError, TypeError, ValueError):
        return ("REVIEW", "date", None)
    if end <= start:
        return ("NO_MATCH", "sequence", None)
    days = (end-start).days
    if bid.get("date_authority") != "issuer":
        return ("REVIEW", "publication_date_not_issuer_confirmed", days)
    return ("SOURCE_MATCH", "exact_curated_scope_and_official_issue_date", days)


def report(doc):
    return [
        {"signal": signal["id"], "bid": bid["id"], "status": status, "reason": reason, "days": days}
        for signal in doc["signals"]
        for bid in doc["procurement"]
        for status, reason, days in [evaluate(signal, bid)]
    ]


if __name__ == "__main__":
    document = json.loads(Path(__file__).with_name("2026-10-29_sample.json").read_text())
    results = report(document)
    print(json.dumps({"observations": len(results),
        "source_matches": sum(x["status"] == "SOURCE_MATCH" for x in results),
        "reviews": sum(x["status"] == "REVIEW" for x in results),
        "no_matches": sum(x["status"] == "NO_MATCH" for x in results),
        "results": results}, indent=2))
