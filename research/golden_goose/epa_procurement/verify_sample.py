"""Fail-closed offline review of *curated* EPA-to-procurement evidence.

This never fetches or authenticates origin pages. Even an accepted receipt is a
reviewable claim about public source contents, not proof of a future opportunity.
"""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ISSUER_HOSTS = {
    "guam-waterworks-authority": {"guamwaterworks.org", "www.guamwaterworks.org"},
    "navajo-tribal-utility-authority": {"ntua.com", "www.ntua.com"},
}
NOTICE_HOSTS = {
    "guam-waterworks-authority": {"notices.guam.gov"},
}
NOTICE_PATH_PATTERN = re.compile(r"/notice_detail/[1-9][0-9]*\Z")


def trusted(url, hosts):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname in hosts
                and not parsed.username and not parsed.password
                and not parsed.fragment)
    except (TypeError, ValueError):
        return False


def parse_iso(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def official_notice_receipt(bid):
    """Demand a notice-specific, dated primary-source reference, not a generic bids URL.

    A syntactically valid receipt is not a substitute for human/source verification
    of its URL, title, and date; this is a provenance completeness gate only.
    """
    receipt = bid.get("issuer_notice")
    if not isinstance(receipt, dict):
        return "missing_issuer_notice"
    if receipt.get("source_kind") != "issuer_public_notice":
        return "issuer_notice_kind"
    url = receipt.get("url")
    if not trusted(url, NOTICE_HOSTS.get(bid.get("agency"), set())):
        return "issuer_notice_source"
    parsed = urlparse(url)
    if not NOTICE_PATH_PATTERN.fullmatch(parsed.path) or parsed.query or parsed.params:
        return "issuer_notice_not_specific"
    title = receipt.get("title")
    bid_id = bid.get("bid_number")
    bid_title = bid.get("bid_title")
    if (not isinstance(title, str) or not isinstance(bid_id, str)
            or not isinstance(bid_title, str) or not bid_id.strip()
            or title != bid_title or bid_id not in title):
        return "issuer_notice_title"
    published = parse_iso(receipt.get("published_on"))
    observed = parse_iso(receipt.get("observed_on"))
    if not published or not observed or published > observed:
        return "issuer_notice_date"
    if published != parse_iso(bid.get("issue_date")):
        return "issuer_notice_date_conflict"
    return None


def evaluate(signal, bid):
    if signal.get("agency") != bid.get("agency"):
        return ("NO_MATCH", "agency", None)
    if signal.get("facility") != bid.get("facility"):
        return ("NO_MATCH", "facility", None)
    if signal.get("scope") != bid.get("scope"):
        return ("REVIEW", "scope_not_exact", None)
    if not trusted(signal.get("url"), {"epa.gov", "www.epa.gov"}):
        return ("REVIEW", "signal_source", None)
    parsed_signal = urlparse(signal.get("url"))
    if not parsed_signal.path.startswith(("/enforcement/", "/newsreleases/")):
        return ("REVIEW", "signal_not_specific", None)
    if not trusted(bid.get("url"), ISSUER_HOSTS.get(bid.get("agency"), set())):
        return ("REVIEW", "bid_source", None)
    start = parse_iso(signal.get("date"))
    end = parse_iso(bid.get("issue_date"))
    if not start or not end:
        return ("REVIEW", "date", None)
    if end <= start:
        return ("NO_MATCH", "sequence", None)
    days = (end-start).days
    if bid.get("date_authority") != "issuer":
        return ("REVIEW", "publication_date_not_issuer_confirmed", days)
    receipt_problem = official_notice_receipt(bid)
    if receipt_problem:
        return ("REVIEW", receipt_problem, days)
    return ("SOURCE_MATCH", "curated_exact_scope_with_dated_primary_notice_receipt", days)


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
