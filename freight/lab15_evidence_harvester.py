"""RETALLY Lab 15: bounded, public metadata discovery for independent LTL audit evidence.

Intentionally does not download/store third-party invoices, access private APIs,
validate financial claims, or clear rights. Saved leads are NOT admitted cases.
All network operations are disabled by default and query only fixed public APIs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from ipaddress import ip_address
import json
from pathlib import Path
import re
import socket
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SCHEMA = 1
MAX_RESPONSE = 1_500_000
MAX_LEADS = 5_000
MAX_NEW_PER_RUN = 60
MAX_PER_FEED = 20
TIMEOUT = 10
USER_AGENT = "RETALLY-Lab15-Public-Metadata/1.0 (research-only)"
API_HOSTS = frozenset({"catalog.data.gov", "dataverse.harvard.edu", "api.datacite.org", "api.github.com"})
LEAD_HOSTS = frozenset({"catalog.data.gov", "dataverse.harvard.edu", "doi.org", "github.com", "www.gao.gov", "document.epiq11.com"})
SOURCES = (
    ("data_gov", "https://catalog.data.gov/api/3/action/package_search?" + urlencode({"q": "freight invoice", "rows": "25"})),
    ("data_gov", "https://catalog.data.gov/api/3/action/package_search?" + urlencode({"q": "freight billing audit", "rows": "25"})),
    ("dataverse", "https://dataverse.harvard.edu/api/search?" + urlencode({"q": "freight invoice", "type": "dataset", "per_page": "25"})),
    ("dataverse", "https://dataverse.harvard.edu/api/search?" + urlencode({"q": "less than truckload", "type": "dataset", "per_page": "25"})),
    ("datacite", "https://api.datacite.org/dois?" + urlencode({"query": "freight invoice", "page[size]": "25"})),
    ("datacite", "https://api.datacite.org/dois?" + urlencode({"query": "LTL freight", "page[size]": "25"})),
    ("github", "https://api.github.com/search/repositories?" + urlencode({"q": "freight invoice dataset in:name,description", "per_page": "25"})),
)


class Rejected(ValueError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def verify_url(url: object, *, api: bool = False) -> str:
    if not isinstance(url, str) or len(url) > 850 or any(ord(c) < 33 for c in url):
        raise Rejected("INVALID_URL")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if (parsed.scheme != "https" or not host or parsed.port not in (None, 443)
                or parsed.username or parsed.password or parsed.fragment):
            raise Rejected("INVALID_URL")
        if host not in (API_HOSTS if api else LEAD_HOSTS):
            raise Rejected("UNAPPROVED_DOMAIN")
        if not parsed.path.startswith("/") or parsed.path.startswith("//"):
            raise Rejected("INVALID_PATH")
        if re.search(r"(?i)(token|secret|password|signature|apikey|auth|session|email|access_key)=", parsed.query):
            raise Rejected("CREDENTIAL_IN_URL")
        if "@" in parsed.path or "%40" in parsed.path.lower():
            raise Rejected("CONTACT_IN_PATH")
    except ValueError as exc:
        raise Rejected("INVALID_URL") from exc
    return url


def sanitize_title(value: object) -> str:
    if not isinstance(value, str):
        return ""
    title = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b", "[contact omitted]", value)
    title = re.sub(r"(?<!\w)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\w)", "[phone omitted]", title)
    title = " ".join(title.split())
    title = "".join(c for c in title if c.isprintable() and c not in "<>\\")
    return title[:150]


def relevant(value: object) -> bool:
    if not isinstance(value, str):
        return False
    s = value.casefold()
    return bool(("freight" in s and ("invoice" in s or "audit" in s or "bill" in s or "ltl" in s))
                or ("less than truckload" in s and ("rate" in s or "shipment" in s))
                or ("ltl" in s and ("invoice" in s or "audit" in s)))


def public_addresses(host: str) -> None:
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise Rejected("DNS_LOOKUP_FAILED") from exc
    if not records:
        raise Rejected("DNS_EMPTY")
    for item in records:
        ip = ip_address(item[4][0])
        if not ip.is_global:
            raise Rejected("DNS_NOT_PUBLIC")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Rejected("REDIRECT_BLOCKED")


def fetch_json(url: str) -> object:
    verify_url(url, api=True)
    public_addresses(urlsplit(url).hostname or "")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Encoding": "identity"}, method="GET")
    with build_opener(NoRedirect).open(request, timeout=TIMEOUT) as response:
        if response.status != 200 or response.geturl() != url:
            raise Rejected("BAD_RESPONSE")
        mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
        if mime not in ("application/json", "application/vnd.github+json"):
            raise Rejected("NOT_JSON")
        body = response.read(MAX_RESPONSE + 1)
    if not body or len(body) > MAX_RESPONSE:
        raise Rejected("BAD_SIZE")
    return json.loads(body)


def source_items(provider: str, data: object) -> list[tuple[str, str]]:
    if not isinstance(data, dict):
        raise Rejected("BAD_PROVIDER_DATA")
    result = []
    if provider == "data_gov":
        rows = data.get("result", {}).get("results", []) if isinstance(data.get("result"), dict) else []
        for item in rows[:MAX_PER_FEED] if isinstance(rows, list) else []:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_-]{3,140}", name):
                continue
            title = item.get("title", "")
            if relevant((str(title) + " " + str(item.get("notes", "")))[:1000]):
                result.append(("https://catalog.data.gov/dataset/" + quote(name), str(title)))
    elif provider == "dataverse":
        block = data.get("data", {})
        rows = block.get("items", []) if isinstance(block, dict) else []
        for item in rows[:MAX_PER_FEED] if isinstance(rows, list) else []:
            if isinstance(item, dict) and item.get("type") == "dataset" and relevant(str(item.get("name", "")) + " " + str(item.get("description", ""))[:1000]):
                result.append((item.get("url", ""), item.get("name", "")))
    elif provider == "datacite":
        rows = data.get("data", [])
        for item in rows[:MAX_PER_FEED] if isinstance(rows, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("attributes"), dict):
                continue
            a = item["attributes"]
            titles = a.get("titles", [])
            title = " ".join(str(x.get("title", "")) for x in titles if isinstance(x, dict)) if isinstance(titles, list) else ""
            doi = a.get("doi", "")
            if isinstance(doi, str) and re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", doi) and relevant(title):
                result.append(("https://doi.org/" + doi, title))
    elif provider == "github":
        rows = data.get("items", [])
        for item in rows[:MAX_PER_FEED] if isinstance(rows, list) else []:
            if isinstance(item, dict) and relevant(str(item.get("name", "")) + " " + str(item.get("description", ""))):
                result.append((item.get("html_url", ""), item.get("name", "")))
    else:
        raise Rejected("UNKNOWN_PROVIDER")
    return result


def new_lead(url: str, title: object, provider: str, seen: str) -> dict:
    url = verify_url(url)
    title = sanitize_title(title)
    if not title or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", seen):
        raise Rejected("INVALID_LEAD")
    return {"id": sha256(url.encode("utf-8")).hexdigest(), "url": url,
            "title": title, "provider": provider, "first_seen": seen,
            "status": "CANDIDATE_ONLY_RIGHTS_AND_TRUTH_UNVERIFIED",
            "invoice_bytes_archived": False, "customer_use_authorized": False,
            "rated_ground_truth_verified": False, "actual_cash_recovery_verified": False}


def blank_ledger() -> dict:
    base = {"schema_version": SCHEMA, "lab": 15, "scope": "PUBLIC_METADATA_ONLY_NO_CUSTOMER_DOCUMENTS", "leads": []}
    return {**base, "digest_sha256": digest(base)}


def validate_ledger(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != {"schema_version", "lab", "scope", "leads", "digest_sha256"}:
        raise Rejected("BAD_LEDGER_SCHEMA")
    if data["schema_version"] != SCHEMA or data["lab"] != 15 or data["scope"] != "PUBLIC_METADATA_ONLY_NO_CUSTOMER_DOCUMENTS":
        raise Rejected("BAD_LEDGER_SCOPE")
    rows = data["leads"]
    if not isinstance(rows, list) or len(rows) > MAX_LEADS:
        raise Rejected("BAD_LEDGER_ROWS")
    if len({row.get("id") for row in rows if isinstance(row, dict)}) != len(rows):
        raise Rejected("DUPLICATE_ID")
    for row in rows:
        if not isinstance(row, dict) or row != new_lead(row.get("url"), row.get("title"), row.get("provider"), row.get("first_seen")):
            raise Rejected("UNAPPROVED_LEDGER_PROMOTION")
    if data["digest_sha256"] != digest({key: data[key] for key in data if key != "digest_sha256"}):
        raise Rejected("LEDGER_DIGEST_MISMATCH")
    return data


def run(ledger: dict, seeds: object, *, network: bool = False, transport=None, now: datetime | None = None) -> tuple[dict, dict]:
    """Return (append-only ledger, transient run summary). No external calls by default."""
    validate_ledger(ledger)
    if not isinstance(seeds, dict) or seeds.get("schema_version") != 1 or not isinstance(seeds.get("seeds"), list):
        raise Rejected("BAD_SEEDS")
    seen_date = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
    existing = {entry["id"]: entry for entry in ledger["leads"]}
    new_count = 0
    errors = []
    fetch = transport or fetch_json
    collected = []
    for item in seeds["seeds"]:
        if not isinstance(item, dict) or set(item) != {"url", "title"}:
            raise Rejected("BAD_SEED_ENTRY")
        collected.append(new_lead(item["url"], item["title"], "previously_observed_public_url", seen_date))
    if network:
        for provider, url in SOURCES:
            try:
                payload = fetch(verify_url(url, api=True))
                for link, title in source_items(provider, payload):
                    try:
                        collected.append(new_lead(link, provider.replace("_", " ") + " freight research candidate", provider, seen_date))
                    except (Rejected, ValueError, TypeError):
                        continue
            except (Rejected, ValueError, TypeError, TimeoutError, OSError, json.JSONDecodeError):
                errors.append(provider + ":FETCH_OR_PARSE_FAILED")
    for item in collected:
        if item["id"] not in existing and new_count < MAX_NEW_PER_RUN and len(existing) < MAX_LEADS:
            existing[item["id"]] = item
            new_count += 1
    base = {"schema_version": SCHEMA, "lab": 15, "scope": "PUBLIC_METADATA_ONLY_NO_CUSTOMER_DOCUMENTS", "leads": sorted(existing.values(), key=lambda r: r["id"])}
    result = {**base, "digest_sha256": digest(base)}
    report = {"status": "UNVERIFIED_PUBLIC_SOURCE_LEADS_ONLY", "scan_date": seen_date,
              "public_api_network_used": bool(network), "api_queries_attempted": len(SOURCES) if network else 0,
              "api_query_failures": errors, "new_leads": new_count, "total_leads": len(existing),
              "customer_documents_saved": 0, "confirmed_rate_errors": 0,
              "claims_or_marketing_approved": False, "source_manifest_digest": result["digest_sha256"]}
    return result, report


def main() -> None:
    base = Path(__file__).resolve().parent / "research"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=base / "lab15_candidate_ledger.json")
    parser.add_argument("--seeds", type=Path, default=base / "lab15_public_seeds.json")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--network", action="store_true", help="Explicitly permit fixed public metadata API GETs")
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding="utf-8")) if args.ledger.exists() else blank_ledger()
    seeds = json.loads(args.seeds.read_text(encoding="utf-8"))
    revised, report = run(ledger, seeds, network=args.network)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(revised, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "new_leads", "total_leads", "api_queries_attempted", "api_query_failures")}, sort_keys=True))


if __name__ == "__main__":
    main()
