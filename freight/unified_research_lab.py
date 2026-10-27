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
import os
import re
import socket
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENGINES = ("freightrecovery", "permitplate", "capturebrief", "recoveryos")
# GitHub discovery now prioritizes FreightRecovery 7/10 planned slots,
# preserving bounded secondary discovery and all four nightly regressions.
DISCOVERY_ROTATION = (
    "freightrecovery", "freightrecovery", "permitplate",
    "freightrecovery", "freightrecovery", "capturebrief",
    "freightrecovery", "freightrecovery", "recoveryos",
    "freightrecovery",
)
ROOT = Path(__file__).resolve().parent / "research_lab"
LEDGER = ROOT / "leads.json"
MAX_ENTRIES = 3000
MAX_NEW_PER_RUN = 40
MAX_BODY = 1_500_000
SEARCHES = {
    "freightrecovery": ("freight invoice", "freight tariff", "freight invoice dataset"),
    "permitplate": ("NYC building permit", "DOB NOW approved permit", "NYC DOB permit issuance"),
    "capturebrief": ("federal contract opportunities", "federal contract awards", "federal solicitations dataset"),
    "recoveryos": ("accounts payable invoice", "vendor payment transparency", "accounts payable invoice dataset"),
}
SOURCE_HOSTS = frozenset({
    "catalog.data.gov", "github.com", "zenodo.org", "www.gao.gov", "www.cbca.gov",
    "data.cityofnewyork.us", "sam.gov", "api.usaspending.gov",
    "www.penninecare.nhs.uk", "media.cadc.uscourts.gov",
    "www2.fmc.gov", "www.fmc.gov", "www.sec.gov", "www.stb.gov",
    "www.eia.gov", "psc.ky.gov", "www.justice.gov",
})
API_HOSTS = frozenset({"api.github.com", "zenodo.org", "api.gsa.gov", "api.us.socrata.com",
                       "retally-unified-research-scout.jayp19386.workers.dev"})
SEEDS = {
    "freightrecovery": (
        "https://www.gao.gov/products/b-160344",
        "https://www.gao.gov/products/b-143246",
        "https://www.gao.gov/products/b-215958",  # Initial 1984 53/55 decision OVERRULED in 1986.
        "https://www.gao.gov/products/b-215958-2",  # Controlling Feb 18 1986 GAO reconsideration; GSA deduction sustained.
        "https://www.gao.gov/products/b-165091",  # Distinct tariff; published $179.80 sustained deduction only.
        "https://www.gao.gov/products/b-221594-0",  # GAO invalidated historical rejected-tender $220.75 deduction; negative only.
        "https://www.gao.gov/products/b-189100",  # GAO 1977 original GBL A-6018184 classification; historical $2634.38 deduction only.
        "https://www.gao.gov/products/b-213717-0",  # GAO 1984 sustained $525.31 GSA classification deduction, historical-only.
        "https://www.gao.gov/products/b-192856",  # 1979 GAO physically tested acoustic-tile sample; $939.42 upheld GSA setoff, historical only.
        "https://www.gao.gov/products/b-191258",  # 1978 GAO reversed $33.30 GSA setoff; later carrier repayment NOT verified.
        "https://www.gao.gov/products/b-143458",  # 1961 adjudicated $155.30, exact historical 6000-lb minimum x $2.51/cwt; original tariff/invoice bytes NOT held.
        "https://www.justice.gov/usao-edca/pr/menlo-worldwide-services-inc-and-its-subcontractor-estes-pay-us-13-million-resolve",  # DOJ 2016 explicitly reports $13m PAID by Menlo/Estes, aggregate government settlement, NOT customer invoice truth.
        "https://www.justice.gov/archives/opa/pr/freight-carriers-agree-pay-685-million-resolve-allegations-knowingly-presenting-false-claims",  # DOJ 2022 AGREED approx $6.85m YRC/Roadway/Yellow; cleared payment NOT verified.
        "https://www2.fmc.gov/readingroom/docs/2022%28I%29/%2801%29%202022%28I%29%20Initial%20Decision.pdf",  # FMC Bridgewell $24,328.80 adjudicated real 2022 shipper fee reparations principal; no original bank custody.
        "https://www2.fmc.gov/readingroom/docs/2022%28I%29/%2802%29%202022%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf",  # Jan 2026 administrative final $28,289.31 principal+interest due; receipt status separate.
        "https://www2.fmc.gov/readingroom/docs/2025%28I%29/%2801%29%202025%28I%29%20Initial%20Decision.pdf",  # HPL $23,600 disputed quote/invoice gap but initial decision awards ZERO reparations.
        "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20-Order%20of%20Dismissal.pdf",  # Nov 2024 official signed settlement: $4650 unpaid demurrage CANCEL obligation; previous paid charges refund right WAIVED, not cash.
        "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20Not.%20Not%20Review.pdf",  # Dec 10 2024 FMC administratively final signed settlement, not original shipping invoice.
        "https://www2.fmc.gov/readingroom/docs/2036%28I%29/%2807%29%202036%28I%29%20Initial%20Decision%20%28with%20Appendices%20A-B%29.pdf",  # Jul 2026 Jimex: five FMC-reported paid detention invoices $1975, INITIAL $11972.07 principal award plus interest, no finality/bank proof.
        "https://www2.fmc.gov/readingroom/docs/2036%28I%29/2036%28I%29%20Order%20Denying%20Respondent%27s%20Request%20for%20Extension%20of%20Time%20to%20File%20Petition%20for%20Reconsideration.pdf",  # Jul 23 request for deadline extension DENIED, not a finality notice.
        "https://www.gao.gov/products/b-121220-0",  # Historical 1964 GAO: who bore transportation expense vs who initially paid is a separate documentary-proof question; NOT current private-law decree.
        "https://www.cbca.gov/files/decisions/2020/SULLIVAN_08-06-20_6578-RATE__AARE_LOGISTICS%2C_LLC%20%28Decision%29.pdf",  # CBCA seven GSA overcharge notices rejected, carrier refund not verified.
        "https://www.cbca.gov/files/decisions/2024/LESTER_08-08-24_8051-RATE__JAMES_FORWARDING_COMPANY_INC%20%28DECISION%29.pdf",  # CBCA unpaid original invoice carrier claim time barred, NOT an overcharge.
        "https://www.cbca.gov/files/decisions/2009/GILMORE_10-29-09_1317-RATE__UNION_PACIFIC_RAILROAD_508.pdf",  # CBCA: 12 original public BOL-keyed Treasury offsets reversed for timeliness, carrier bank refund UNVERIFIED.
        "https://www.cbca.gov/files/decisions/2014/ZISCHKAU_05-14-14_CBCA%203467-RATE__IN_THE_MATTER_OF_TOTAL_QUALITY_LOGISTICS_LLC_.pdf",  # CBCA: GSA's 70 paid-detention invoice recoupment demands invalid, conflicting 2-cent source totals.
        "https://www.gao.gov/products/b-221663-0",  # GAO 1986 agent-versus-interline ruling; amount UNKNOWN, not invoice scoring.
        "https://www.gao.gov/products/b-139340",  # GAO 1959 exclusive-use GBL; historical $523.60/$451.95/$71.65, not modern truth.
        # New source-bound reported numeric cases; original invoices not held.
        "https://www.gao.gov/products/b-191257",  # 1978 Yellow Freight $828 / $796 / $32.
        "https://www.gao.gov/products/b-152744-0",  # 1964 $611.80 paid / $122.20; conditional review.
        "https://www.gao.gov/products/b-148465",  # 1962 $546.88 paid / $61.22; SCOTUS caveat.
        "https://www.gao.gov/products/b-143048",  # 1960 two shipments; $130.30 aggregate only.
        "https://www.gao.gov/products/b-146511-2",  # 1965 conflicting reclaim figures; offset $20.74.
        # Published v1 official decision and price-source locators only.
        "https://media.cadc.uscourts.gov/opinions/docs/2026/04/25-1104-2170734.pdf",
        "https://www2.fmc.gov/readingroom/docs/2030%28I%29/%2815%29%202030%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf",
        "https://www.fmc.gov/wp-content/uploads/2025/06/8-F.M.C.2d.pdf",
        "https://www.sec.gov/Archives/edgar/data/1507615/000150761511000033/exhibit101.htm",
        "https://www.sec.gov/Archives/edgar/data/1552000/000155200026000009/mplx-20251231xex1056.htm",
        "https://www.stb.gov/reports-data/waybill/",
        "https://www.eia.gov/petroleum/gasdiesel/",
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
    headers = {
        "User-Agent": "RETALLY-UnifiedResearch/1.0 (metadata only)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    if urlsplit(url).hostname == "api.gsa.gov":
        key = os.environ.get("RETALLY_DATAGOV_API_KEY", "")
        if not key:
            raise ResearchError("DATAGOV_V4_KEY_REQUIRED")
        headers["X-Api-Key"] = key
    req = Request(url, headers=headers, method="GET")
    try:
        with build_opener(NoRedirect).open(req, timeout=12) as response:
            if response.status != 200 or response.geturl() != url:
                raise ResearchError("HTTP_RESPONSE_REJECTED")
            mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if mime not in ("application/json", "application/vnd.github+json"):
                raise ResearchError("UNSUPPORTED_CONTENT_TYPE")
            body = response.read(MAX_BODY + 1)
    except HTTPError as exc:
        raise ResearchError("HTTP_STATUS_" + str(exc.code)) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ResearchError("PUBLIC_SOURCE_UNAVAILABLE") from exc
    if not body or len(body) > MAX_BODY:
        raise ResearchError("RESPONSE_SIZE_REJECTED")
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # A public metadata endpoint may serve malformed or incorrectly encoded
        # JSON without preventing independent engine lanes from progressing.
        # Never echo untrusted provider response text into run diagnostics.
        raise ResearchError("SOURCE_JSON_INVALID") from exc
    if type(data) is not dict:
        raise ResearchError("SOURCE_JSON_INVALID")
    return data


PERMITPLATE_KNOWN_NON_DOB_DATASET_IDS = frozenset(("43nn-pn8j", "pitm-atqc", "qcdj-rwhu", "fpeh-f7ci"))


def permitplate_url_in_scope(url: str) -> bool:
    """Reject verified wrong-topic public source pointers from permit research."""
    path = urlsplit(url).path.lower()
    return (re.search(r"(?i)(restaurant|inspection|yelp|food[-_ ]?safety|dine[-_ ]?safe)", path) is None
            and path.rstrip("/").rsplit("/", 1)[-1] not in PERMITPLATE_KNOWN_NON_DOB_DATASET_IDS)


def permitplate_catalog_in_scope(resource: dict) -> bool:
    """Reject non-DOB catalogs; metadata is not independent permit issuance."""
    title = resource.get("name") if type(resource) is dict else None
    return bool(type(title) is str
                and re.search(r"\b(dob|building|construction)\b", title, re.I)
                and re.search(r"\b(permits?|filings?|applications?|certificates?)\b",
                              title, re.I)
                and not re.search(r"\b(restaurant|inspection)\b", title, re.I))


def original_nyc_catalog_entry(item: dict) -> bool:
    """Only accept original publisher datasets, not community-saved views.

    A public NYC host and DOB title are insufficient for source provenance.
    This remains unverified source metadata, not issuance truth or reuse rights.
    """
    if type(item) is not dict:
        return False
    resource, metadata = item.get("resource"), item.get("metadata")
    return bool(type(resource) is dict and type(metadata) is dict
                and resource.get("provenance") == "official"
                and resource.get("type") == "dataset"
                and type(resource.get("parent_fxf")) is list
                and not resource["parent_fxf"]
                and metadata.get("domain") == "data.cityofnewyork.us"
                and permitplate_catalog_in_scope(resource))


# Purely advisory public catalog **metadata** screening; no original source
# bytes, scraped descriptions, identities, metadata titles or approvals persist.
TOPIC_TERMS = {
    "freightrecovery": ("freight", "trucking", "truckload", "ltl", "bill of lading",
                        "shipment invoice", "shipping cost", "carrier invoice",
                        "carrier rate", "transportation cost", "logistics invoice",
                        "tariff"),
    "permitplate": ("dob now", "nyc dob", "nyc building permit",
                    "new york building permit", "building permit",
                    "construction permit", "permit issuance", "approved permits",
                    "dob filing"),
    "capturebrief": ("sam gov", "usaspending", "federal contract",
                     "federal procurement", "federal solicitation",
                     "government contract", "government procurement",
                     "public tender", "public procurement", "rfp",
                     "contract awards"),
    "recoveryos": ("accounts payable", "account payable", "vendor payment",
                   "supplier payment", "supplier invoice",
                   "invoice reconciliation", "payment reconciliation",
                   "invoice dataset", "duplicate invoice",
                   "public sector spending", "spending transparency"),
}


def metadata_in_scope(engine: str, provider: str, row: dict) -> bool:
    """Search-result topic hint only; never rights, relevance or outcome proof."""
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    if provider not in ("github", "zenodo"):
        raise ResearchError("UNSUPPORTED_PROVIDER")
    if type(row) is not dict:
        return False
    if provider == "github":
        fields = (row.get("name"), row.get("description"))
    else:
        metadata = row.get("metadata")
        title = metadata.get("title") if type(metadata) is dict else None
        fields = (title if title is not None else row.get("title"),)
    def norm(value):
        return re.sub(r"[^a-z0-9]+", " ", value[:512].lower()).strip() if type(value) is str else ""
    body = " ".join(filter(None, map(norm, fields)))
    if not body:
        return False
    padded = " " + body + " "
    if engine == "permitplate" and any(
            token in padded for token in (" restaurant ", " inspection ",
                                           " food safety ", " yelp ",
                                           " dining out ")):
        return False
    return any(" " + term + " " in padded for term in TOPIC_TERMS[engine])


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


def merge_sources(doc: dict, engine: str, urls: list[str], seen: str, *,
                  first_seen_overrides: dict[str, str] | None = None) -> tuple[dict, int]:
    validate_ledger(doc)
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    items = {r["id"]: dict(r) for r in doc["entries"]}
    added = 0
    for url in urls:
        candidate = source_record(url, engine, (first_seen_overrides or {}).get(url, seen))
        if engine == "permitplate" and not permitplate_url_in_scope(candidate["url"]):
            continue
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
    return DISCOVERY_ROTATION[int(now.timestamp() // 300) % len(DISCOVERY_ROTATION)]


MAX_SCOUT_MIRROR_PAGES = 6
SCOUT_PAGE_SIZE = 100


def scout_url(engine: str, *, before: str | None = None) -> str:
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    args = {"engine": engine, "limit": str(SCOUT_PAGE_SIZE)}
    if before is not None:
        if type(before) is not str or not re.fullmatch(r"[1-9]\d{0,11}", before):
            raise ResearchError("SCOUT_CURSOR_INVALID")
        args["before"] = before
    return ("https://retally-unified-research-scout.jayp19386.workers.dev/feed?" +
            urlencode(args))


def parse_scout_rows(engine: str, data: dict, now: datetime | None = None
                     ) -> list[tuple[str, str | None]]:
    """Only accept lane-scoped public URLs; preserve D1 observation dates when mirroring."""
    if (type(data) is not dict or data.get("engine") != engine
            or data.get("scope") != "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA"
            or type(data.get("sources")) is not list):
        raise ResearchError("UNTRUSTED_SCOUT_FEED")
    if now is not None and now.tzinfo is None:
        raise ResearchError("TIMEZONE_REQUIRED")
    if len(data["sources"]) > SCOUT_PAGE_SIZE:
        raise ResearchError("SCOUT_PAGE_OVER_LIMIT")
    rows = []
    seen_urls = set()
    for record in data["sources"]:
        if type(record) is not dict or type(record.get("url")) is not str:
            raise ResearchError("INVALID_SCOUT_RECORD")
        url = safe_url(record["url"])
        if url in seen_urls:
            raise ResearchError("DUPLICATE_SCOUT_RECORD")
        seen_urls.add(url)
        first_seen = None
        if now is not None:
            first_seen = record.get("first_seen")
            if (type(first_seen) is not str
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", first_seen)):
                raise ResearchError("SCOUT_OBSERVATION_DATE_INVALID")
            try:
                day = date.fromisoformat(first_seen)
            except ValueError as exc:
                raise ResearchError("SCOUT_OBSERVATION_DATE_INVALID") from exc
            if day > now.date() or day < date(2020, 1, 1):
                raise ResearchError("SCOUT_OBSERVATION_DATE_INVALID")
        rows.append((url, first_seen))
    return rows


def scan(engine: str, fetch=get_json) -> tuple[list[str], list[str]]:
    """Return canonical source locators only. No source rows, titles, or PII."""
    if engine not in ENGINES:
        raise ResearchError("INVALID_ENGINE")
    q1, q2, q3 = SEARCHES[engine]
    urls, errors = [], []
    # Use public metadata endpoints that work without credentials. The old
    # Data.gov CKAN v3 endpoint was retired in 2026. The official v4 API
    # requires an API key; never use its rate-limited DEMO_KEY in cron.
    feeds = [
        # Durable metadata accumulated independently if GitHub cron is absent.
        ("cloudflare-failover", "scout", scout_url(engine)),
        ("github:" + q1, "github", "https://api.github.com/search/repositories?" +
         urlencode({"q": q1 + " in:name,description", "per_page": "15"})),
        ("github:" + q3, "github", "https://api.github.com/search/repositories?" +
         urlencode({"q": q3 + " in:name,description", "per_page": "15"})),
        ("zenodo:" + q2, "zenodo", "https://zenodo.org/api/records?" +
         urlencode({"q": q2, "size": "15"})),
        ("zenodo:" + q3, "zenodo", "https://zenodo.org/api/records?" +
         urlencode({"q": q3, "size": "15"})),
    ]
    if engine == "permitplate":
        feeds.append(("nyc-official-open-data", "socrata",
                      "https://api.us.socrata.com/api/catalog/v1?" +
                      urlencode({"domains": "data.cityofnewyork.us",
                                 "search_context": "data.cityofnewyork.us",
                                 "provenance": "official", "only": "dataset",
                                 "q": "NYC DOB building permit",
                                 "limit": "20"})))
    if os.environ.get("RETALLY_DATAGOV_API_KEY"):
        feeds.append(("data.gov-v4:" + q1, "datagov-v4",
                      "https://api.gsa.gov/technology/datagov/v4/search?" +
                      urlencode({"q": q1, "per_page": "20"})))
    successful = 0
    for label, provider, address in feeds:
        try:
            data = fetch(address)
            if provider == "scout":
                urls.extend(url for url, _ in parse_scout_rows(engine, data))
            elif provider == "datagov-v4":
                rows = data.get("results", [])
                if type(rows) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in rows[:20]:
                    if type(item) is not dict:
                        continue
                    slug = item.get("slug")
                    dcat = item.get("dcat")
                    access = dcat.get("accessLevel") if type(dcat) is dict else None
                    if (type(slug) is str and re.fullmatch(r"[a-z0-9_-]{3,140}", slug)
                            and access == "public"):
                        urls.append("https://catalog.data.gov/dataset/" + slug)
            elif provider == "github":
                rows = data.get("items", [])
                if type(rows) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in rows[:15]:
                    if type(item) is not dict:
                        continue
                    url = item.get("html_url")
                    if (type(url) is str and re.fullmatch(
                        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", url
                    ) and metadata_in_scope(engine, "github", item)):
                        urls.append(url)
            elif provider == "socrata":
                rows = data.get("results", [])
                if type(rows) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in rows[:20]:
                    if type(item) is not dict:
                        continue
                    resource = item.get("resource")
                    ident = resource.get("id") if type(resource) is dict else None
                    if (type(ident) is str and re.fullmatch(r"[a-z0-9]{4}-[a-z0-9]{4}", ident)
                            and original_nyc_catalog_entry(item)):
                        urls.append("https://data.cityofnewyork.us/d/" + ident)
            else:
                hits = data.get("hits", {}).get("hits", [])
                if type(hits) is not list:
                    raise ResearchError("INVALID_PROVIDER_ROWS")
                for item in hits[:15]:
                    if (type(item) is dict and re.fullmatch(r"[1-9][0-9]{0,14}", str(item.get("id", "")))
                            and metadata_in_scope(engine, "zenodo", item)):
                        urls.append("https://zenodo.org/records/" + str(item["id"]))
            successful += 1
        except ResearchError as exc:
            # These identifiers come from our own bounded error enum, never
            # untrusted response content or credential-bearing request URLs.
            errors.append(label + ":" + str(exc))
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(label + ":" + type(exc).__name__)
    if successful == 0:
        raise ResearchError("ALL_PUBLIC_FEEDS_UNAVAILABLE")
    # Preserve trusted feed ordering: a late-running GitHub job should first
    # mirror the scout backlog, not repeatedly consume only search front pages.
    return list(dict.fromkeys(urls)), errors


def mirror_scout_all(*, ledger: Path, now: datetime, fetch=get_json) -> dict:
    """Read-only fetch from four independent scout lanes into one rights-held branch."""
    if now.tzinfo is None:
        raise ResearchError("TIMEZONE_REQUIRED")
    original = read_ledger(ledger)
    revised = original
    per_engine = {}
    errors = []
    for engine in ENGINES:
        try:
            observed = {}
            cursor = None
            pages = 0
            reached_cap = False
            for _ in range(MAX_SCOUT_MIRROR_PAGES):
                data = fetch(scout_url(engine, before=cursor))
                rows = parse_scout_rows(engine, data, now)
                for url, seen in rows:
                    if url in observed:
                        raise ResearchError("SCOUT_OVERLAPPING_PAGES")
                    observed[url] = seen
                pages += 1
                following = data.get("next_cursor")
                if following is None:
                    break
                if (type(following) is not str
                        or not re.fullmatch(r"[1-9]\d{0,11}", following)
                        or len(rows) != SCOUT_PAGE_SIZE
                        or (cursor is not None and int(following) >= int(cursor))):
                    raise ResearchError("SCOUT_CURSOR_INVALID")
                cursor = following
            else:
                if cursor is not None:
                    reached_cap = True
                    errors.append(engine + ":SCOUT_PAGE_CAP_REACHED")
            # Only validated public URLs and observation dates enter the ledger.
            # The existing forty-new-source cap applies per lane per GitHub run.
            revised, added = merge_sources(
                revised, engine, list(observed), now.date().isoformat(),
                first_seen_overrides=observed)
            per_engine[engine] = {
                "available": len(observed), "new": added,
                "pages_read": pages, "page_cap_reached": reached_cap,
            }
        except ResearchError as exc:
            errors.append(engine + ":" + str(exc))
            per_engine[engine] = {"available": 0, "new": 0, "pages_read": 0, "page_cap_reached": False}
        except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
            # Keep a single unexpectedly malformed scout response isolated.
            # Diagnostics expose only a bounded, code-owned exception category.
            errors.append(engine + ":UNTRUSTED_SCOUT_RESPONSE_" + type(exc).__name__)
            per_engine[engine] = {"available": 0, "new": 0, "pages_read": 0, "page_cap_reached": False}
    if revised != original:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps(revised, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return {"new_leads": sum(row["new"] for row in per_engine.values()),
            "total_leads": len(revised["entries"]), "per_engine": per_engine,
            "feed_errors": errors, "third_party_documents_saved": 0,
            "customer_contact_actions": 0, "production_changes": 0}


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
    parser.add_argument("--mirror-scout-all", action="store_true",
                        help="Mirror all four public metadata lanes, no external source bytes")
    parser.add_argument("--engine", choices=ENGINES)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.mirror_scout_all:
        if args.live or args.engine:
            parser.error("--mirror-scout-all must be used on its own")
        print(json.dumps(mirror_scout_all(ledger=args.ledger, now=now), sort_keys=True))
        return
    engine = args.engine or current_engine(now)
    report = run(engine=engine, live=args.live, ledger=args.ledger, now=now)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
