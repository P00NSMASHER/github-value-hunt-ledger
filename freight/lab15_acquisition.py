"""RETALLY Lab 15: bounded public freight-evidence discovery and custody metadata.

Never purchases data, authenticates to third-party accounts, contacts anyone, or
commits original invoices. The public GitHub ledger holds only source pointers,
checksums, and admission holds. Customer/third-party document rights are NOT
conferred by a public URL. No financial truth or recovery is inferred here.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

ROOT = Path(__file__).resolve().parent
SEEDS = ROOT / "lab15" / "sources.json"
LEDGER = ROOT / "lab15" / "evidence_ledger.json"
MAX_DOC_BYTES = 2_000_000
MAX_CATALOG_BYTES = 1_000_000
MAX_CANDIDATES_PER_RUN = 25
MAX_CATALOG_ITEMS = 40
NETWORK_HOSTS = frozenset({
    "www.gao.gov", "gao.gov", "zenodo.org", "dataverse.harvard.edu",
    "api.github.com",
})
SOURCE_HOSTS = frozenset({
    "www.gao.gov", "gao.gov", "psc.ky.gov", "document.epiq11.com",
    "github.com", "zenodo.org", "dataverse.harvard.edu",
})
RECORD_STATES = frozenset({
    "SOURCE_REGISTERED_RIGHTS_HOLD", "PUBLIC_SOURCE_FINGERPRINTED",
    "DISCOVERED_METADATA_ONLY",
})
RIGHTS_HOLD = "SOURCE_AND_CUSTOMER_REUSE_RIGHTS_UNVERIFIED"
USER_AGENT = "RETALLY-EvidenceResearch/1.0 (public metadata only; https://www.retallyrecovery.com/)"
SEARCHES = (
    ("github", "https://api.github.com/search/repositories?q=freight+invoice+dataset+in%3Aname%2Cdescription&sort=updated&order=desc&per_page=20"),
    ("zenodo", "https://zenodo.org/api/records/?q=%22freight%20invoice%22&size=20"),
    ("dataverse", "https://dataverse.harvard.edu/api/search?q=freight%20invoice&type=dataset&per_page=20"),
)


class EvidenceError(ValueError):
    """Non-sensitive bounded fetch or source-admission failure."""


@dataclass(frozen=True)
class HTTPResult:
    status: int
    final_url: str
    content_type: str
    body: bytes


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("REDIRECT_NOT_AUTHORIZED")


def safe_url(url: str, hosts: frozenset[str]) -> str:
    if not isinstance(url, str) or len(url) > 650 or any(
        ord(c) < 32 or ord(c) == 127 for c in url
    ):
        raise EvidenceError("UNSAFE_URL")
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError as exc:
        raise EvidenceError("UNSAFE_URL") from exc
    if (u.scheme != "https" or not u.hostname or u.hostname not in hosts
            or u.username is not None or u.password is not None
            or u.fragment or port not in (None, 443) or "\\" in url):
        raise EvidenceError("UNSAFE_URL")
    if re.search(r"%0[0-9a-f]|%1[0-9a-f]|%7f|%5c", url, re.I):
        raise EvidenceError("UNSAFE_URL")
    path = u.path or "/"
    if ".." in path.split("/") or "/./" in path:
        raise EvidenceError("UNSAFE_URL")
    authority = u.hostname + (":443" if port == 443 else "")
    return urlunsplit(("https", authority, path, u.query, ""))


def source_id(url: str) -> str:
    return "src-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def timestamp(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        raise EvidenceError("NAIVE_TIME")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def source_record(url: str, kind: str, first_seen: str, *,
                  title: str = "", discovered_by: str = "SEED") -> dict:
    url = safe_url(url, SOURCE_HOSTS)
    if kind not in ("GAO_DECISION", "PUBLIC_REGULATORY_EXHIBIT",
                    "PUBLIC_BANKRUPTCY_EXHIBIT", "DATASET_CATALOG_LEAD"):
        raise EvidenceError("INVALID_KIND")
    return {
        "id": source_id(url),
        "url": url,
        "kind": kind,
        "title": scrub_title(title),
        "discovered_by": discovered_by,
        "first_seen": first_seen,
        "content_version": 0,
        "sha256": None,
        "bytes_seen": 0,
        "state": ("DISCOVERED_METADATA_ONLY" if discovered_by != "SEED"
                  else "SOURCE_REGISTERED_RIGHTS_HOLD"),
        "rights": RIGHTS_HOLD,
        "raw_document_stored": False,
        "commercial_test_approved": False,
        "actual_payment_verified": False,
        "independent_invoice_error_verified": False,
        "recovery_verified": False,
    }


def scrub_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    val = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", title)).split())
    # Search titles may contain private contacts; omit them entirely.
    if ("@" in val or re.search(r"(?:\+?\d[\s().-]*){10,}", val)
            or any(ord(c) < 32 for c in val)):
        return "[REDACTED]"
    return re.sub(r"[\x00-\x1f\x7f]", "", val)[:140]


def load_seeds(path: Path = SEEDS) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if type(raw) is not dict or raw.get("schema_version") != 1:
        raise EvidenceError("BAD_SEED_MANIFEST")
    seeds = raw.get("sources")
    if not isinstance(seeds, list) or not (1 <= len(seeds) <= 30):
        raise EvidenceError("BAD_SEED_MANIFEST")
    out = []
    ids = set()
    for row in seeds:
        if set(row) != {"url", "kind", "title"}:
            raise EvidenceError("BAD_SEED_FIELDS")
        clean = safe_url(row["url"], SOURCE_HOSTS)
        if source_id(clean) in ids:
            raise EvidenceError("DUPLICATE_SEED")
        ids.add(source_id(clean))
        # Only government-authored GAO decisions can be auto-read; carrier
        # invoices embedded in public filings remain metadata-only.
        if row["kind"] == "GAO_DECISION":
            if urlsplit(clean).hostname not in {"gao.gov", "www.gao.gov"}:
                raise EvidenceError("FALSE_GAO_SOURCE")
        elif row["kind"] == "PUBLIC_REGULATORY_EXHIBIT":
            if urlsplit(clean).hostname != "psc.ky.gov":
                raise EvidenceError("FALSE_REGULATOR_SOURCE")
        elif row["kind"] == "PUBLIC_BANKRUPTCY_EXHIBIT":
            if urlsplit(clean).hostname != "document.epiq11.com":
                raise EvidenceError("FALSE_COURT_SOURCE")
        else:
            raise EvidenceError("BAD_SEED_KIND")
        out.append({**row, "url": clean})
    return out


def validate_ledger(ledger: dict) -> None:
    if type(ledger) is not dict or set(ledger) != {"schema_version", "records"}:
        raise EvidenceError("BAD_LEDGER")
    if ledger["schema_version"] != 1 or type(ledger["records"]) is not list:
        raise EvidenceError("BAD_LEDGER")
    seen = set()
    required = set(source_record("https://www.gao.gov/products/b-143246", "GAO_DECISION",
                                 "2026-01-01T00:00:00Z"))
    for record in ledger["records"]:
        if type(record) is not dict or set(record) != required:
            raise EvidenceError("BAD_RECORD_SCHEMA")
        url = safe_url(record["url"], SOURCE_HOSTS)
        ident = source_id(url)
        if record["id"] != ident or ident in seen:
            raise EvidenceError("BAD_RECORD_ID")
        seen.add(ident)
        host = urlsplit(url).hostname
        expected_hosts = {
            "GAO_DECISION": {"gao.gov", "www.gao.gov"},
            "PUBLIC_REGULATORY_EXHIBIT": {"psc.ky.gov"},
            "PUBLIC_BANKRUPTCY_EXHIBIT": {"document.epiq11.com"},
            "DATASET_CATALOG_LEAD": {"github.com", "zenodo.org",
                                     "dataverse.harvard.edu"},
        }
        if record["kind"] not in expected_hosts or host not in expected_hosts[record["kind"]]:
            raise EvidenceError("SOURCE_KIND_HOST_MISMATCH")
        permitted_publisher = {
            "github.com": "GITHUB", "zenodo.org": "ZENODO",
            "dataverse.harvard.edu": "DATAVERSE",
        }
        if record["kind"] == "DATASET_CATALOG_LEAD":
            if record["discovered_by"] != permitted_publisher[host]:
                raise EvidenceError("UNVERIFIED_CATALOG_PUBLISHER")
        elif record["discovered_by"] != "SEED":
            raise EvidenceError("SEED_ORIGIN_MISMATCH")
        if (record["state"] not in RECORD_STATES
                or record["rights"] != RIGHTS_HOLD
                or record["raw_document_stored"] is not False
                or record["commercial_test_approved"] is not False
                or record["actual_payment_verified"] is not False
                or record["independent_invoice_error_verified"] is not False
                or record["recovery_verified"] is not False
                or type(record["content_version"]) is not int
                or record["content_version"] < 0
                or type(record["bytes_seen"]) is not int
                or record["bytes_seen"] < 0):
            raise EvidenceError("FALSE_APPROVAL_IN_LEDGER")
        digest = record["sha256"]
        if digest is not None and (not isinstance(digest, str)
                 or not re.fullmatch(r"[0-9a-f]{64}", digest)
                 or record["content_version"] < 1 or record["bytes_seen"] < 1
                 or record["kind"] != "GAO_DECISION"):
            raise EvidenceError("INVALID_SOURCE_RECEIPT")
        if digest is None and (record["content_version"] != 0 or record["bytes_seen"] != 0
                               or record["state"] == "PUBLIC_SOURCE_FINGERPRINTED"):
            raise EvidenceError("INVALID_SOURCE_RECEIPT")
        if digest is not None and record["state"] != "PUBLIC_SOURCE_FINGERPRINTED":
            raise EvidenceError("INVALID_SOURCE_RECEIPT")
        if (not isinstance(record["title"], str)
                or record["title"] != scrub_title(record["title"])
                or not isinstance(record["first_seen"], str)
                or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",
                                    record["first_seen"])):
            raise EvidenceError("BAD_RECORD_TEXT")
    if len(seen) > 20000:
        raise EvidenceError("LEDGER_CAP_EXCEEDED")


def read_ledger(path: Path = LEDGER) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_ledger(raw)
    return raw


def http_get(url: str) -> HTTPResult:
    """Only exact allowlisted HTTPS hosts; redirects fail instead of chasing."""
    url = safe_url(url, NETWORK_HOSTS)
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html,application/pdf",
    })
    opener = build_opener(HTTPSHandler(), _NoRedirect())
    try:
        with opener.open(req, timeout=12) as response:
            status = int(response.status)
            final = response.geturl()
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            max_size = MAX_CATALOG_BYTES if urlsplit(url).hostname in {
                "api.github.com", "zenodo.org", "dataverse.harvard.edu"
            } else MAX_DOC_BYTES
            body = response.read(max_size + 1)
    except EvidenceError:
        raise
    except Exception as exc:
        raise EvidenceError("PUBLIC_FETCH_UNAVAILABLE") from exc
    return HTTPResult(status, final, mime, body)


def verify_response(url: str, response: HTTPResult, *,
                    catalog: bool = False) -> bytes:
    expected = safe_url(url, NETWORK_HOSTS)
    if not isinstance(response, HTTPResult) or response.status != 200:
        raise EvidenceError("PUBLIC_FETCH_UNAVAILABLE")
    if safe_url(response.final_url, NETWORK_HOSTS) != expected:
        raise EvidenceError("REDIRECT_NOT_AUTHORIZED")
    max_size = MAX_CATALOG_BYTES if catalog else MAX_DOC_BYTES
    body = response.body
    if (not isinstance(body, bytes) or not body or len(body) > max_size):
        raise EvidenceError("BOUNDED_PAYLOAD_FAILURE")
    allowed_mime = ({"application/json"} if catalog
                    else {"text/html", "application/xhtml+xml", "application/pdf"})
    mime = response.content_type.split(";", 1)[0].strip().lower()
    if mime not in allowed_mime:
        raise EvidenceError("CONTENT_TYPE_MISMATCH")
    if mime == "application/pdf" and not body.startswith(b"%PDF-"):
        raise EvidenceError("INVALID_PDF_MAGIC")
    if mime != "application/pdf" and not catalog and b"<" not in body[:2000]:
        raise EvidenceError("INVALID_HTML")
    return body


def catalog_leads(provider: str, data: dict) -> list[tuple[str, str]]:
    """Provider-specific metadata adapters. Never fetch candidate URLs."""
    if not isinstance(data, dict):
        raise EvidenceError("BAD_CATALOG")
    rows: list[tuple[str, str]] = []
    if provider == "github":
        items = data.get("items")
        if not isinstance(items, list):
            raise EvidenceError("BAD_CATALOG")
        for row in items[:MAX_CATALOG_ITEMS]:
            if not isinstance(row, dict):
                continue
            name = row.get("full_name", "")
            description = row.get("description") or ""
            if not isinstance(name, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,70}/[A-Za-z0-9_.-]{1,100}", name
            ):
                continue
            rows.append(("https://github.com/" + name, name + " — " + str(description)))
    elif provider == "zenodo":
        hits = data.get("hits", {})
        items = hits.get("hits", []) if isinstance(hits, dict) else None
        if not isinstance(items, list):
            raise EvidenceError("BAD_CATALOG")
        for row in items[:MAX_CATALOG_ITEMS]:
            if not isinstance(row, dict):
                continue
            ident = str(row.get("id", ""))
            if ident.isdigit() and len(ident) <= 18:
                meta = row.get("metadata", {})
                title = meta.get("title", "") if isinstance(meta, dict) else ""
                rows.append(("https://zenodo.org/records/" + ident, str(title)))
    elif provider == "dataverse":
        outer = data.get("data", {})
        items = outer.get("items", []) if isinstance(outer, dict) else None
        if not isinstance(items, list):
            raise EvidenceError("BAD_CATALOG")
        for row in items[:MAX_CATALOG_ITEMS]:
            if not isinstance(row, dict) or row.get("type") != "dataset":
                continue
            pid = row.get("global_id", "")
            if isinstance(pid, str) and re.fullmatch(
                r"doi:10\.\d{4,9}/[A-Za-z0-9_.:/-]{3,130}", pid, re.I
            ):
                title = row.get("name", "")
                rows.append((
                    "https://dataverse.harvard.edu/dataset.xhtml?persistentId=" +
                    quote(pid, safe=""), str(title)
                ))
    else:
        raise EvidenceError("UNKNOWN_CATALOG")
    out = []
    for url, title in rows:
        normalized = scrub_title(title)
        haystack = normalized.casefold()
        if re.search(r"\b(synthetic|fictional|template|mock|demo|sample generated)\b",
                     haystack):
            continue
        if (("freight" in haystack or "ltl" in haystack)
                and ("invoice" in haystack or "audit" in haystack
                     or "overcharge" in haystack)):
            out.append((safe_url(url, SOURCE_HOSTS), normalized))
    return out


def run_cycle(ledger: dict, seed_rows: list[dict], *, live: bool = False,
              fetch=None, now: datetime | None = None,
              pause=None) -> tuple[dict, dict]:
    """Atomic in-memory refresh; actual persistence belongs to the caller."""
    validate_ledger(ledger)
    observed = timestamp(now)
    records = {r["id"]: dict(r) for r in ledger["records"]}
    retrieve = fetch if fetch is not None else http_get
    sleeper = pause if pause is not None else time.sleep
    report = {"observed_at": observed, "mode": "PUBLIC_METADATA_LIVE" if live else "OFFLINE",
              "seeded": 0, "discovered": 0, "new_fingerprints": 0,
              "changed_fingerprints": 0, "fetch_holds": 0,
              "catalog_holds": 0, "raw_documents_stored": 0,
              "verified_real_customer_outcomes": 0,
              "commercial_data_admissions": 0}
    for row in seed_rows:
        url = safe_url(row["url"], SOURCE_HOSTS)
        ident = source_id(url)
        if ident not in records:
            records[ident] = source_record(url, row["kind"], observed,
                                           title=row["title"])
            report["seeded"] += 1
        existing = records[ident]
        if existing["kind"] != row["kind"] or existing["discovered_by"] != "SEED":
            raise EvidenceError("SEED_IDENTITY_DRIFT")
        if live and row["kind"] == "GAO_DECISION":
            try:
                payload = verify_response(url, retrieve(url))
                digest = hashlib.sha256(payload).hexdigest()
                if existing["sha256"] != digest:
                    if existing["sha256"] is not None:
                        report["changed_fingerprints"] += 1
                    else:
                        report["new_fingerprints"] += 1
                    existing["sha256"] = digest
                    existing["bytes_seen"] = len(payload)
                    existing["content_version"] += 1
                    existing["state"] = "PUBLIC_SOURCE_FINGERPRINTED"
            except EvidenceError:
                report["fetch_holds"] += 1
            sleeper(0.25)
    if live:
        remaining = MAX_CANDIDATES_PER_RUN
        for provider, url in SEARCHES:
            try:
                payload = verify_response(url, retrieve(url), catalog=True)
                parsed = json.loads(payload.decode("utf-8"))
                leads = catalog_leads(provider, parsed)
                for link, title in leads:
                    if remaining < 1:
                        break
                    ident = source_id(link)
                    if ident not in records:
                        records[ident] = source_record(
                            link, "DATASET_CATALOG_LEAD", observed,
                            title=title, discovered_by=provider.upper())
                        report["discovered"] += 1
                        remaining -= 1
            except (EvidenceError, UnicodeDecodeError, json.JSONDecodeError):
                report["catalog_holds"] += 1
            sleeper(0.25)
    outcome = {"schema_version": 1,
               "records": sorted(records.values(), key=lambda x: x["id"])}
    validate_ledger(outcome)
    report["total_sources"] = len(outcome["records"])
    report["unverified_rights"] = len(outcome["records"])
    return outcome, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Fetch bounded public metadata (requires explicit env gate).")
    parser.add_argument("--seeds", type=Path, default=SEEDS)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    if args.live and os.environ.get("RETALLY_LAB15_PUBLIC_FETCH_ENABLED") != "1":
        raise SystemExit("PUBLIC_FETCH_EXPLICIT_ENV_GATE_REQUIRED")
    seeds = load_seeds(args.seeds)
    ledger = read_ledger(args.ledger)
    updated, report = run_cycle(ledger, seeds, live=args.live)
    # A public source URL is not a license to republish an original invoice.
    # Therefore ONLY the private-free, schema-validated metadata ledger persists.
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
