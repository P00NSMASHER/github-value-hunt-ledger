"""RETALLY Unified Research Lab: unattended public-data discovery, not financial truth.

Four engines share one metadata-only, rights-held public-source catalog.
No private records, raw documents, customer data, authenticated sources, claims,
payment instructions, or outbound customer contact enter this pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENGINES = ("freightrecovery", "permitplate", "capturebrief", "recoveryos")
ROOT = Path(__file__).resolve().parent / "research_lab"
LEDGER = ROOT / "leads.json"
MAX_ENTRIES = 3000
MAX_NEW_PER_RUN = 40
MAX_BODY = 1_500_000
SEARCHES = {
    "freightrecovery": ("freight invoice", "freight tariff", "freight invoice dataset"),
    "permitplate": ("NYC restaurant inspection", "NYC building permits", "restaurant license open data"),
    "capturebrief": ("federal contract opportunities", "federal contract awards", "federal solicitations dataset"),
    "recoveryos": ("accounts payable invoice", "vendor payment transparency", "accounts payable invoice dataset"),
}
SOURCE_HOSTS = frozenset({
    "catalog.data.gov", "github.com", "zenodo.org", "www.gao.gov",
    "data.cityofnewyork.us", "sam.gov", "api.usaspending.gov",
    "www.penninecare.nhs.uk",
})
API_HOSTS = frozenset({"catalog.data.gov", "api.github.com", "zenodo.org"})
SEEDS = {
    "freightrecovery": (
        "https://www.gao.gov/products/b-160344",
        "https://www.gao.gov/products/b-143246",
    ),
    "permitplate": (
        "https://data.cityofnewyork.us/d/43nn-pn8j",
        "https://data.cityofnewyork.us/d/w9ak-ipjd",
    ),
    "capturebrief": (
        "https://sam.gov/opportunities",
        "https://api.usaspending.gov/docs/endpoints",
    ),
    "recoveryos": (
        "https://www.penninecare.nhs.uk/download_file/5855/277",
    ),
}
RIGHTS = "UNVERIFIED_EXTERNAL_SOURCE_RIGHTS_HOLD"
TRUTH = "UNVERIFIED_NOT_INDEPENDENT_GROUND_TRUTH"
FIELDS = frozenset({
    "id", "url", "engines", "publisher", "first_seen", "rights_state",
    "truth_state", "document_bytes_stored", "commercial_reuse_authorized",
    "independent_ground_truth", "independent_payment_verified",
    "recovered_cash_verified",
})
FALSE_FIELDS = (
    "document_bytes_stored", "commercial_reuse_authorized",
    "independent_ground_truth", "independent_payment_verified",
    "recovered_cash_verified",
)


class ResearchError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ResearchError("REDIRECT_BLOCKED")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def safe_url(url: str, *, api: bool = False) -> str:
    if (not isinstance(url, str) or len(url) > 850 or
            any(ord(c) < 33 or ord(c) == 127 for c in url) or
            "\\" in url or "%0" in url.lower()):
        raise ResearchError("UNSAFE_URL")
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError as exc:
        raise ResearchError("UNSAFE_URL") from exc
    if (p.scheme != "https" or p.hostname not in
            (API_HOSTS if api else SOURCE_HOSTS) or port not in (None, 443)
            or p.username is not None or p.password is not None or p.fragment
            or (p.query and not api)
            or ".." in p.path.split("/") or p.path.startswith("//")):
        raise ResearchError("UNSAFE_URL")
    if api and re.search(r"(?i)(token|secret|password|key|auth|session)=", p.query):
        raise ResearchError("UNSAFE_API_QUERY")
    return url


def global_dns(host: str) -> None:
    try:
        ips = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ResearchError("DNS_UNAVAILABLE") from exc
    if not ips or any(not ipaddress.ip_address(i[4][0]).is_global for i in ips):
        raise ResearchError("NONPUBLIC_NETWORK")


def get_json(url: str) -> dict:
    safe_url(url, api=True)
    global_dns(urlsplit(url).hostname or "")
    req = Request(url, headers={
        "User-Agent": "RETALLY-UnifiedResearch/1.0 (metadata only)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }, method="GET")
    try:
        with build_opener(NoRedirect).open(req, timeout=12) as response:
            if response.status != 200 or response.geturl() != url:
                raise ResearchError("HTTP_RESPONSE_REJECTED")
            mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if mime not in ("application/json", "application/vnd.github+json"):
                raise ResearchError("UNSUPPORTED_CONTENT_TYPE")
            body = response.read(MAX_BODY + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ResearchError("PUBLIC_SOURCE_UNAVAILABLE") from exc
    if not body or len(body) > MAX_BODY:
        raise ResearchError("RESPONSE_SIZE_REJECTED")
    data = json.loads(body)
    if type(data) is not dict:
        raise ResearchError("SOURCE_JSON_INVALID")
    return data


def source_record(url: str, engine: str, seen: str) -> dict:
    safe_url(url)
    if engine not in ENGINES or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", seen):
        raise ResearchError("INVALID_SOURCE_METADATA")
    return {
        "id": digest(url), "url": url, "engines": [engine],
        "publisher": urlsplit(url).hostname, "first_seen": seen,
        "rights_state": RIGHTS, "truth_state": TRUTH,
        **{key: False for key in FALSE_FIELDS},
    }


def validate_ledger(doc: dict) -> None:
    if (type(doc) is not dict or set(doc) != {"schema_version", "entries", "entries_sha256"}
            or type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or type(doc["entries"]) is not list or len(doc["entries"]) > MAX_ENTRIES):
        raise ResearchError("INVALID_LEDGER")
    seen = set()
    for row in doc["entries"]:
        if type(row) is not dict or set(row) != FIELDS:
            raise ResearchError("INVALID_RECORD_FIELDS")
        if (type(row["url"]) is not str or safe_url(row["url"]) != row["url"]
                or row["id"] != digest(row["url"]) or row["id"] in seen
                or row["publisher"] != urlsplit(row["url"]).hostname
                or not isinstance(row["first_seen"], str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["first_seen"])
                or type(row["engines"]) is not list or not row["engines"]
                or row["engines"] != sorted(set(row["engines"]))
                or any(x not in ENGINES for x in row["engines"])
                or row["rights_state"] != RIGHTS or row["truth_state"] != TRUTH
                or any(row[k] is not False for k in FALSE_FIELDS)):
            raise ResearchError("UNTRUSTED_RESEARCH_CLAIM")
        seen.add(row["id"])
    if ([x["id"] for x in doc["entries"]] != sorted(seen)
            or doc["entries_sha256"] != digest(doc["entries"])):
        raise ResearchError("LEDGER_INTEGRITY_FAILURE")


def ledger_from(entries: list[dict]) -> dict:
    rows = sorted(entries, key=lambda x: x["id"])
    payload = {"schema_version": 1, "entries": rows,
               "entries_sha256": digest(rows)}
    validate_ledger(payload)
    return payload


def read_ledger(path: Path = LEDGER) -> dict:
    if not path.exists():
        return ledger_from([])
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_ledger(doc)
    return doc


def merge_sources(doc: dict, engine: str, urls: list[str], seen: str) -> tuple[dict, int]:
    validate_ledger(doc)
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    items = {r["id"]: dict(r) for r in doc["entries"]}
    added = 0
    for url in urls:
        candidate = source_record(url, engine, seen)
        key = candidate["id"]
        if key in items:
            row = items[key]
            row["engines"] = sorted(set(row["engines"]) | {engine})
        elif len(items) < MAX_ENTRIES and added < MAX_NEW_PER_RUN:
            items[key] = candidate
            added += 1
    return ledger_from(list(items.values())), added


def current_engine(now: datetime) -> str:
    if now.tzinfo is None:
        raise ResearchError("TIMEZONE_REQUIRED")
    return ENGINES[int(now.timestamp() // 300) % len(ENGINES)]


def scan(engine: str, fetch=get_json) -> tuple[list[str], list[str]]:
    """Return canonical public locators only. Never copy source titles/rows."""
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    q1, q2, q3 = SEARCHES[engine]
    urls, errors = [], []
    feeds = [
        ("data.gov:" + q1, "datagov", "https://catalog.data.gov/api/3/action/package_search?" +
         urlencode({"q": q1, "rows": "25"})),
        ("data.gov:" + q2, "datagov", "https://catalog.data.gov/api/3/action/package_search?" +
         urlencode({"q": q2, "rows": "25"})),
        ("github:" + q3, "github", "https://api.github.com/search/repositories?" +
         urlencode({"q": q3 + " in:name,description", "per_page": "15"})),
        ("zenodo:" + q3, "zenodo", "https://zenodo.org/api/records/?" +
         urlencode({"q": q3, "size": "15"})),
    ]
    successful = 0
    for label, provider, address in feeds:
        try:
            data = fetch(address)
            if provider == "datagov":
                rows = data.get("result", {}).get("results", [])
                if type(rows) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in rows[:25]:
                    if type(item) is not dict:
                        continue
                    slug = item.get("name")
                    if type(slug) is str and re.fullmatch(r"[a-z0-9_-]{3,140}", slug):
                        urls.append("https://catalog.data.gov/dataset/" + slug)
            elif provider == "github":
                rows = data.get("items", [])
                if type(rows) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in rows[:15]:
                    if type(item) is not dict:
                        continue
                    url = item.get("html_url")
                    if type(url) is str and re.fullmatch(
                        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", url
                    ):
                        urls.append(url)
            else:
                hits = data.get("hits", {}).get("hits", [])
                if type(hits) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in hits[:15]:
                    if type(item) is dict and str(item.get("id", "")).isdigit():
                        urls.append("https://zenodo.org/records/" + str(item["id"]))
            successful += 1
        except (ResearchError, ValueError, KeyError, TypeError) as exc:
            errors.append(label + ":" + type(exc).__name__)
    if successful == 0:
        raise ResearchError("ALL_PUBLIC_FEEDS_UNAVAILABLE")
    return sorted(set(urls)), errors


def run(*, engine: str, live: bool, ledger: Path, now: datetime,
        fetch=get_json) -> dict:
    original = read_ledger(ledger)
    urls = list(SEEDS[engine])
    errors = []
    if live:
        candidates, errors = scan(engine, fetch=fetch)
        urls.extend(candidates)
    revised, count = merge_sources(original, engine, urls, now.date().isoformat())
    if revised != original:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps(revised, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return {
        "engine": engine, "network_enabled": live, "new_leads": count,
        "total_leads": len(revised["entries"]), "feed_errors": errors,
        "third_party_documents_saved": 0, "approved_real_truth_cases": 0,
        "customer_contact_actions": 0, "production_changes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Fetch only fixed public metadata APIs")
    parser.add_argument("--engine", choices=ENGINES)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    args = parser.parse_args()
    engine = args.engine or current_engine(datetime.now(timezone.utc))
    report = run(engine=engine, live=args.live, ledger=args.ledger,
                 now=datetime.now(timezone.utc))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
