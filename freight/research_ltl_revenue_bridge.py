"""RETALLY Research Lab 14 / Mission 18: AIES LTL-carrier revenue evidence.

An offline Census-origin, FRED-distributed employer-establishment revenue
comparison. Historical source values NEVER establish customer invoice volume,
recovery rates, legally recoverable claims, paid freight spend, buyer interest,
or any RETALLY earnings. No automatic data download or scheduled tasks.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
import io
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash

BOOK = Path(__file__).parent / "research/AIES_LTL_CARRIER_REVENUE_20261011.json"
EXPECTED_BOOK_GIT_BLOB_SHA1 = "5c0a38eb5fea967c93d96049262fbc04586af275"
SCOPE = "LAB14_CENSUS_AIES_2024_LTL_EMPLOYER_REVENUE_NO_RECOVERY_CLAIMS"
REPORT_SCOPE = "LAB14_AIES_SOURCE_BOUND_LTL_CARRIER_REVENUE_NOT_RECOVERY_TAM"
OBSERVED_ON = date(2026, 10, 11)
RELEASED_ON = date(2026, 9, 3)
UPDATED_ON = date(2026, 9, 10)
YEARS = (2022, 2023, 2024)
RECORDS = {
    "484": {
        "series": "AIES484RCT00US",
        "title": "Truck Transportation, All Establishments: Revenue",
        "values": (423270958, 406651010, 402827246),
    },
    "484121": {
        "series": "AIES484121RCT00US",
        "title": "General Freight Trucking, Long-Distance, Truckload, All Establishments: Revenue",
        "values": (172717339, 163025116, 161329027),
    },
    "484122": {
        "series": "AIES484122RCT00US",
        "title": "General Freight Trucking, Long-Distance, Less Than Truckload, All Establishments: Revenue",
        "values": (65688461, 64651167, 65096292),
    },
}
FIELDS = {
    "schema_version", "scope", "observed_on", "publisher", "distributor",
    "census_2024_release_date", "fred_series_last_updated_on",
    "cfs_origin_naics_population", "naics_classification",
    "geographic_scope", "metric", "units", "source_family",
    "observation_method", "official_release_url",
    "census_aies_api_documentation_url", "fred_aies_series",
    "legacy_2022_sas_comparator", "evidence_guards", "reviewer_note",
}
SERIES_FIELDS = {"naics", "series_id", "industry_name", "source_url", "observations"}
OBS_FIELDS = {"year", "revenue_thousand_usd"}
OLD_FIELDS = {
    "series_id", "source_url", "metric", "year", "revenue_million_usd",
    "unit", "interchangeable_with_aies",
}
GUARDS_FALSE = (
    "direct_official_census_api_or_original_ftp_bytes_replayed_in_repo",
    "three_fred_series_independent_market_surveys",
    "legacy_sas_series_interchangeable_with_aies",
    "cfs_goods_values_are_carrier_revenue",
    "naics_484122_includes_all_ltl_transport",
    "aies_revenue_equals_auditable_customer_invoice_volume",
    "actual_recovered_money_proven",
    "verified_invoice_error_prevalence",
    "ltl_recovery_tam_established", "buyer_demand_established",
    "commercial_or_outreach_authority",
    "customer_or_carrier_data_ingested", "new_lab_created",
    "data_source_terms_or_publisher_digital_signature_audited",
)
DEFAULT_SOURCE_OBSERVATION = (
    "PUBLIC_CENSUS_RELEASE_AND_FRED_SERIES_WEB_VIEW_NO_ORIGINAL_CENSUS_API_OR_CSV_BYTE_REPLAY"
)
FRED_MAX_BYTES = 128 * 1024


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _date(x: object) -> date:
    if type(x) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        raise ValueError("SOURCE_DATE_NOT_ISO")
    result = date.fromisoformat(x)
    if result.isoformat() != x:
        raise ValueError("SOURCE_DATE_NONCANONICAL")
    return result


def _pct(numerator: int, denominator: int) -> str:
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise ValueError("INVALID_SHARE_INPUT")
    return str((Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ))


def _growth(new: int, old: int) -> str:
    if type(new) is not int or type(old) is not int or new < 0 or old <= 0:
        raise ValueError("INVALID_YEAR_COMPARISON")
    return _pct(new - old, old)


def _billions(thousands: int) -> str:
    return str((Decimal(thousands) / Decimal(1_000_000)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    ))


def validate_catalog(book: object, *, as_of: date) -> list[str]:
    """Validate closed schema plus observed source figures and provenance."""
    try:
        errors = []
        if type(book) is not dict or set(book) != FIELDS or book.get("schema_version") != 1:
            return ["INVALID_CLOSED_AIES_SNAPSHOT_SCHEMA"]
        if book.get("scope") != SCOPE or (
            book.get("metric") != "ANNUAL_EMPLOYER_ESTABLISHMENT_INDUSTRY_REVENUE_NOT_FREIGHT_INVOICES"
        ):
            errors.append("AIES_REVENUE_METRIC_OR_SCOPE_TAMPER")
        if (_date(book.get("observed_on")) != OBSERVED_ON or
            _date(book.get("census_2024_release_date")) != RELEASED_ON or
            _date(book.get("fred_series_last_updated_on")) != UPDATED_ON or
            OBSERVED_ON > as_of or not RELEASED_ON <= UPDATED_ON <= OBSERVED_ON):
            errors.append("AIES_SOURCE_CHRONOLOGY_INVALID")
        expected_literals = {
            "publisher": "U.S. Census Bureau",
            "distributor": "Federal Reserve Bank of St. Louis (FRED)",
            "geographic_scope": "UNITED_STATES_NATIONAL",
            "units": "THOUSANDS_OF_NOMINAL_US_DOLLARS",
            "naics_classification": "2017_NAICS_LONG_DISTANCE_LTL_484122_EMPLOYER_BUSINESSES",
            "source_family": "US_CENSUS_AIES_SINGLE_UNDERLYING_PUBLISHER_VIA_FRED_NOT_INDEPENDENT_SAMPLES",
            "observation_method": DEFAULT_SOURCE_OBSERVATION,
            "official_release_url": "https://www.census.gov/newsroom/press-releases/2026/2024-aies-data-release.html",
            "census_aies_api_documentation_url": "https://www.census.gov/data/developers/data-sets/aies.html",
            "cfs_origin_naics_population": "CFS_2022_GOODS_VALUE_MODE111_NAICS4931_INCLUDES484_NOT_AIES_CARRIER_INDUSTRY_REVENUE",
        }
        for field, expected in expected_literals.items():
            if book.get(field) != expected:
                errors.append("SOURCE_IDENTITY_OR_POPULATION_TAMPER:" + field)
        flags = book.get("evidence_guards")
        if type(flags) is not dict or set(flags) != set(GUARDS_FALSE) | {"actual_customer_invoice_cases_examined"}:
            errors.append("INVALID_COMMERCIAL_EVIDENCE_GUARDS")
        else:
            for field in GUARDS_FALSE:
                if flags.get(field) is not False:
                    errors.append("FALSE_COMMERCIAL_OR_SOURCE_PROMOTION:" + field)
            if type(flags.get("actual_customer_invoice_cases_examined")) is not int or (
                flags["actual_customer_invoice_cases_examined"] != 0
            ):
                errors.append("UNSUPPORTED_REAL_INVOICE_COUNT")
        note = book.get("reviewer_note")
        if (type(note) is not str or len(note) < 210 or len(note) > 1200 or
            "invoice" not in note.lower() or "CFS" not in note or "FRED" not in note or
            "not" not in note.lower()):
            errors.append("MISSING_EXPLICIT_RESEARCH_EVIDENCE_BOUNDARY")
        series = book.get("fred_aies_series")
        if type(series) is not list or len(series) != len(RECORDS):
            return errors + ["INCOMPLETE_AIES_SERIES_SET"]
        seen = set()
        for i, entry in enumerate(series):
            if type(entry) is not dict or set(entry) != SERIES_FIELDS:
                errors.append("SERIES_" + str(i) + "_SCHEMA_OR_EXTRA_PRIVATE_FIELDS")
                continue
            naics = entry.get("naics")
            if naics not in RECORDS or naics in seen:
                errors.append("AIES_NAICS_DUPLICATED_OR_NOT_IN_APPROVED_SET")
                continue
            seen.add(naics)
            spec = RECORDS[naics]
            if (entry.get("series_id") != spec["series"] or
                entry.get("industry_name") != spec["title"] or
                entry.get("source_url") != "https://fred.stlouisfed.org/data/" + spec["series"]):
                errors.append("AIES_SOURCE_SERIES_OR_NAICS_NOT_FROZEN:" + naics)
            rows = entry.get("observations")
            if type(rows) is not list or len(rows) != 3:
                errors.append("MISSING_AIES_YEARLY_OBSERVATIONS:" + naics)
                continue
            years = set()
            for row in rows:
                if type(row) is not dict or set(row) != OBS_FIELDS:
                    errors.append("INVALID_OBSERVATION_FIELDS:" + naics)
                    continue
                y = row.get("year")
                val = row.get("revenue_thousand_usd")
                if type(y) is not int or y not in YEARS or y in years:
                    errors.append("DUPLICATE_OR_IMPROPER_AIES_YEAR:" + naics)
                    continue
                years.add(y)
                if type(val) is not int or val != spec["values"][YEARS.index(y)]:
                    errors.append("AIES_SOURCE_VALUE_CHANGED_OR_WRONG_UNITS:" + naics + ":" + str(y))
            if years != set(YEARS):
                errors.append("AIES_YEAR_COVERAGE_MISMATCH:" + naics)
        if seen != set(RECORDS):
            errors.append("MISSING_REQUIRED_TRUCKING_REVENUE_CATEGORY")
        legacy = book.get("legacy_2022_sas_comparator")
        if type(legacy) is not dict or set(legacy) != OLD_FIELDS or legacy != {
            "series_id": "REVEF484122ALLEST",
            "source_url": "https://fred.stlouisfed.org/data/REVEF484122ALLEST",
            "metric": "LEGACY_2022_SERVICES_ANNUAL_SURVEY_NOT_AIES_SERIES",
            "year": 2022, "revenue_million_usd": 68411,
            "unit": "MILLIONS_OF_NOMINAL_US_DOLLARS",
            "interchangeable_with_aies": False,
        }:
            errors.append("LEGACY_SAS_AIES_SERIES_SUBSTITUTION_FORBIDDEN")
        if errors:
            return errors
        for y_index in range(3):
            if (RECORDS["484122"]["values"][y_index] +
                RECORDS["484121"]["values"][y_index] >
                RECORDS["484"]["values"][y_index]):
                errors.append("HIERARCHY_PARENT_SMALLER_THAN_CHILDREN")
        return errors
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return ["CORRUPT_AIES_SOURCE_BOOK"]


def _read_book() -> dict:
    raw = BOOK.read_bytes()
    if _git_blob_sha1(raw) != EXPECTED_BOOK_GIT_BLOB_SHA1:
        raise ValueError("PINNED_AIES_SOURCE_GIT_BLOB_DRIFT")
    return json.loads(raw.decode("utf-8"))


def parse_fred_csv(series_id: str, raw: bytes, book: dict) -> dict:
    """Second-stage optional receipt. A FRED download is NOT a Census API download."""
    if series_id not in {x["series"] for x in RECORDS.values()}:
        raise ValueError("UNAUTHORIZED_FRED_SERIES")
    if type(raw) is not bytes or not raw or len(raw) > FRED_MAX_BYTES:
        raise ValueError("FRED_CSV_EMPTY_OR_UNBOUNDED")
    try:
        body = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError("FRED_CSV_NON_UTF8") from exc
    if "\x00" in body:
        raise ValueError("FRED_CSV_BINARY_INJECTION")
    reader = csv.DictReader(io.StringIO(body, newline=""))
    if reader.fieldnames not in (["observation_date", series_id], ["DATE", series_id]):
        raise ValueError("FRED_SOURCE_SERIES_CSV_HEADER_MISMATCH")
    time_col = reader.fieldnames[0]
    parsed = {}
    for i, row in enumerate(reader):
        if i > 160 or None in row:
            raise ValueError("FRED_CSV_ROW_LIMIT_OR_COLUMN_CORRUPTION")
        timestamp = row.get(time_col)
        val = row.get(series_id)
        if type(timestamp) is not str or not re.fullmatch(r"\d{4}-01-01", timestamp):
            raise ValueError("FRED_WRONG_FREQUENCY_OR_DATE")
        year = int(timestamp[:4])
        if year in parsed:
            raise ValueError("FRED_DUPLICATED_ANNUAL_OBSERVATION")
        if year > 2024:
            raise ValueError("NEWER_FRED_YEAR_REQUIRES_RESEARCH_REFRESH_NOT_SILENTLY_IGNORED")
        if type(val) is not str or (val != "." and not re.fullmatch(r"\d{1,13}", val)):
            raise ValueError("FRED_DATA_SUPPRESSED_OR_NOT_INTEGER")
        parsed[year] = val
    source = next(x for x in book["fred_aies_series"] if x["series_id"] == series_id)
    expected = {x["year"]: x["revenue_thousand_usd"] for x in source["observations"]}
    for year in YEARS:
        if parsed.get(year) != str(expected[year]):
            raise ValueError("FRED_CSV_SOURCE_OBSERVATION_MISMATCH:" + str(year))
    return {
        "source_series_id": series_id,
        "csv_sha256": sha256(raw).hexdigest(),
        "verified_observation_years": list(YEARS),
        "verified_values_thousand_usd": [expected[y] for y in YEARS],
        "source_csv_contains_noncustomer_statistics_only": True,
        "downloaded_from_census_origin_api": False,
        "original_census_publisher_signature_proven": False,
    }


def download_fred_csv(series_id: str) -> bytes:
    if series_id not in {x["series"] for x in RECORDS.values()}:
        raise ValueError("FRED_ONLY_THREE_ALLOWLISTED_PUBLIC_SERIES")
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
    req = Request(url, headers={"User-Agent": "RETALLY-Lab14-ResearchVerification/1.0"})
    with urlopen(req, timeout=20) as response:
        if response.geturl() != url:
            raise ValueError("FRED_CSV_SOURCE_REDIRECT_NOT_ALLOWED")
        body = response.read(FRED_MAX_BYTES + 1)
    if len(body) > FRED_MAX_BYTES:
        raise ValueError("FRED_CSV_RESPONSE_TOO_BIG")
    return body


def build_revenue(*, as_of: date, book: dict | None = None,
                  downloaded_csv: dict[str, bytes] | None = None) -> dict:
    if book is None:
        book = _read_book()
    errors = validate_catalog(book, as_of=as_of)
    if errors:
        raise ValueError("INVALID_AIES_LTL_REVENUE_BOOK: " + "; ".join(errors))
    remote = []
    if downloaded_csv is not None:
        expected = {r["series"] for r in RECORDS.values()}
        if type(downloaded_csv) is not dict or set(downloaded_csv) != expected:
            raise ValueError("FRED_REMOTE_VERIFICATION_REQUIRES_ALL_THREE_SERIES")
        remote = [
            parse_fred_csv(spec["series"], downloaded_csv[spec["series"]], book)
            for spec in RECORDS.values()
        ]
    truck = RECORDS["484"]["values"]
    tl = RECORDS["484121"]["values"]
    ltl = RECORDS["484122"]["values"]
    result = {
        "schema_version": 1,
        "scope": REPORT_SCOPE,
        "lab": 14, "new_lab_created": False,
        "as_of": as_of.isoformat(),
        "observed_snapshot_on": book["observed_on"],
        "latest_observed_reference_year": 2024,
        "report_is_not_a_live_2026_revenue_estimate": True,
        "source": {
            "publisher": book["publisher"],
            "distributor": book["distributor"],
            "method": book["observation_method"],
            "source_family": book["source_family"],
            "census_data_released_on": book["census_2024_release_date"],
            "fred_series_updated_on": book["fred_series_last_updated_on"],
            "source_snapshot_git_blob_sha1": EXPECTED_BOOK_GIT_BLOB_SHA1,
            "full_census_origin_api_bytes_replayed": False,
            "fred_public_csv_replay_completed": downloaded_csv is not None,
            "fred_csv_replay_receipts": remote,
        },
        "revenue_by_year": [
            {
                "year": y,
                "ltl_484122_thousand_usd": ltl[i],
                "tl_484121_thousand_usd": tl[i],
                "all_trucking_484_thousand_usd": truck[i],
                "ltl_subset_of_trucking_revenue_share_pct": _pct(ltl[i], truck[i]),
            } for i, y in enumerate(YEARS)
        ],
        "ltl_2024_revenue_billion_usd": _billions(ltl[2]),
        "tl_2024_revenue_billion_usd": _billions(tl[2]),
        "all_trucking_2024_revenue_billion_usd": _billions(truck[2]),
        "ltl_2024_share_of_all_trucking_pct": _pct(ltl[2], truck[2]),
        "ltl_2024_growth_vs_2023_pct": _growth(ltl[2], ltl[1]),
        "ltl_2024_growth_vs_2022_pct": _growth(ltl[2], ltl[0]),
        "ltl_2022_aies_thousand_usd": ltl[0],
        "historical_2022_sas_comparator_million_usd": 68411,
        "legacy_2022_comparator_is_interchangeable": False,
        "legacy_series_cannot_be_spliced_into_aies": True,
        "cross_cfs_shipped_goods_value_division_allowed": False,
        "cfs_2022_mode111_and_aies_484122_populations_are_not_equivalent": True,
        "ltl_invoice_volume_or_share_of_customer_spend_usd": None,
        "ltl_freight_audit_recoverable_tam_usd": None,
        "real_ltl_invoice_cases_observed": 0,
        "verified_invoice_error_rate_pct": None,
        "actual_cash_recovered_usd": None,
        "buyer_demand_proven": False,
        "commercial_uses_or_external_contact_allowed": False,
        "customer_or_carrier_data_ingested": False,
        "source_category_warning": (
            "Census AIES 2024 establishment revenue, NAICS 484122 long-distance "
            "general-freight LTL, is a carrier-industry statistic, not all LTL "
            "freight spend and not paid invoice data. The Census 2022 CFS measures "
            "shipped goods value; CFS mode 111 includes truckload and LTL and its "
            "4931 reporting category groups 484. The three FRED revenue series "
            "share one Census publisher; the legacy SAS 2022 observation comes "
            "from a different survey iteration. No verified billing errors, "
            "contingency fees, buyers or recoveries are measured."
        ),
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def render_html(report: dict) -> str:
    rows = "".join(
        "<tr><th>" + str(x["year"]) + "</th><td>$" +
        escape(_billions(x["ltl_484122_thousand_usd"])) + "B</td><td>$" +
        escape(_billions(x["tl_484121_thousand_usd"])) + "B</td><td>$" +
        escape(_billions(x["all_trucking_484_thousand_usd"])) + "B</td><td>" +
        escape(x["ltl_subset_of_trucking_revenue_share_pct"]) + "%</td></tr>"
        for x in report["revenue_by_year"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY / LTL Revenue Evidence</title><style>'
        'body{background:#f7f9f7;color:#1a342a;font:16px/1.6 system-ui,sans-serif;'
        'margin:0}main{max-width:1060px;margin:45px auto;padding:0 18px}'
        'h1{font-size:clamp(29px,5vw,43px);line-height:1.1}'
        'table{border-collapse:collapse;background:white;width:100%}'
        'td,th{border-bottom:1px solid #ddd;padding:12px;text-align:left}'
        'section{border:1px solid #d4ded8;background:white;border-radius:14px;'
        'padding:20px;margin:20px 0}small{color:#486758}</style></head><body>'
        '<main><small>RETALLY / RESEARCH LAB 14 / MISSION 18 / NOT FOR MARKETING</small>'
        '<h1>Long-distance LTL carrier revenue: not audit recoveries</h1>'
        '<section><h2>2024 Census AIES reference year</h2>'
        '<p>NAICS 484122: <strong>$' +
        escape(report["ltl_2024_revenue_billion_usd"]) +
        ' billion</strong> in revenue at covered employer establishments.</p>'
        '<p>Share of all NAICS 484 trucking revenue: ' +
        escape(report["ltl_2024_share_of_all_trucking_pct"]) +
        '%. Not share of LTL shippers, carriers audited, paid invoices or claims.</p></section>'
        '<section style="overflow:auto"><table><thead><tr><th>Year</th>'
        '<th>NAICS 484122 LTL</th><th>NAICS 484121 truckload</th>'
        '<th>NAICS 484 all trucking</th><th>LTL subset share</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table></section>'
        '<section><h2>Audit and provenance boundary</h2><p>' +
        escape(report["source_category_warning"]) + '</p><p>2024 versus 2023: ' +
        escape(report["ltl_2024_growth_vs_2023_pct"]) +
        '% nominal revenue change. These are survey estimates subject to '
        'sampling and other errors, not exact cash ledgers.</p><p>'
        '2022 legacy SAS LTL revenue was $68,411 million, a different historical '
        'series that is <strong>not substituted</strong> for the AIES $65,688.461 '
        'million 2022 observation.</p><p>FRED CSV byte replay: ' +
        ('complete' if report["source"]["fred_public_csv_replay_completed"]
         else 'not performed in this offline report') +
        ' — this is not an original Census API receipt.</p></section>'
        '<p>Source: <a href="https://fred.stlouisfed.org/series/AIES484122RCT00US">'
        'FRED / Census NAICS 484122</a> and '
        '<a href="https://www.census.gov/newsroom/press-releases/2026/2024-aies-data-release.html">'
        '2024 Census AIES release</a>.</p>'
        '</main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Source-bounded LTL revenue research")
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--verify-fred-csv", action="store_true",
                        help="Optional explicit online source check, not automatic")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of_date)
    csv_map = None
    if args.verify_fred_csv:
        csv_map = {x["series"]: download_fred_csv(x["series"]) for x in RECORDS.values()}
    result = build_revenue(as_of=as_of, downloaded_csv=csv_map)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"aies_ltl_revenue.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out/"aies_ltl_revenue.html").write_text(
        render_html(result), encoding="utf-8")
    print(json.dumps({
        "ltl_2024_revenue_billion_usd": result["ltl_2024_revenue_billion_usd"],
        "commercial_recovery_market_verified": False,
        "fred_csv_replayed": result["source"]["fred_public_csv_replay_completed"],
        "receipt_sha256": result["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
