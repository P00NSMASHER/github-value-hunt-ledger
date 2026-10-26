"""Read-only casebook of GAO-adjudicated historical freight bills.

Independent GAO review of a GSA audit is evidence of a historical decision.
It is NOT independent custody of original invoices, current customer pricing,
a settled customer bank credit, or RETALLY revenue.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from freight.unified_research_lab import ResearchError, digest

FIXTURE = Path(__file__).with_name("fixtures") / "gao_adjudicated_billing_casebook_v1.json"
SCOPE = "INDEPENDENT_GAO_DECISION_REVIEW_OF_GSA_HISTORICAL_AUDITS_ONLY"
SUSTAINED = "GAO_SUSTAINED_GSA_DEDUCTION"
INVALID = "GAO_INVALIDATED_GSA_DEDUCTION"

# Independent, audited expectations: a rehashed or self-consistent forged JSON
# must never change money, the outcome label, rights or source custody.
PINNED = (
    ("B-191257", "1978-07-03", "https://www.gao.gov/products/b-191257",
     "Yellow Freight System, Inc.", "K-3087713", 82800, 79600, 3200,
     SUSTAINED, "HISTORICAL_ROUTE_TENDER_APPLICABILITY"),
    ("B-189100", "1977-12-27", "https://www.gao.gov/products/b-189100",
     "Yellow Freight System, Inc.", "A-6018184", 356718, None, 263438,
     SUSTAINED, "HISTORICAL_COMMODITY_CLASSIFICATION_WITH_CARGO_PHOTO"),
    ("B-213717", "1984-03-20", "https://www.gao.gov/products/b-213717-0",
     "Yellow Freight System, Inc.", None, 121209, 68678, 52531,
     SUSTAINED, "HISTORICAL_LAUNCHER_VS_AIRCRAFT_PARTS_NMFC_CLASSIFICATION"),
    ("B-221594", "1986-09-29", "https://www.gao.gov/products/b-221594-0",
     "Riss International", None, 94200, 72125, 22075,
     INVALID, "HISTORICAL_TENDER_REJECTED_BEFORE_DOD_SHIPMENT"),
)
ROW_KEYS = (
    "case_id", "decision_date", "official_url", "carrier", "gbl_reference",
    "reported_carrier_collected_cents", "reported_gsa_audited_charge_cents",
    "reported_gsa_deducted_cents", "disposition", "issue",
)
ROOT_DEFAULTS = {
    "schema_version": 1,
    "fixture_id": "RETALLY_GAO_ADJUDICATED_HISTORICAL_BILLING_CASEBOOK_V1",
    "reviewed_utc_date": "2026-10-26",
    "publisher": "U.S. Government Accountability Office",
    "scope": SCOPE,
    "source_authority": "GAO_OFFICIAL_DECISION_TRANSCRIPTION_NOT_ORIGINAL_INVOICE_BYTES",
    "source_html_bytes_acquired": False,
    "source_html_bytes_sha256": None,
    "original_invoice_and_tariff_bytes_held": False,
    "independent_customer_rate_and_payment_chain_verified": False,
    "independent_training_holdout_verified": False,
    "commercial_customer_engine_reuse_approved": False,
    "verified_retally_customer_cases": 0,
    "verified_retally_recovered_cash_cents": 0,
}


def validate_casebook(data: object) -> dict:
    if type(data) is not dict or set(data) != set(ROOT_DEFAULTS) | {"cases"}:
        raise ResearchError("GAO_CASEBOOK_ROOT_SCHEMA_INVALID")
    for key, expected in ROOT_DEFAULTS.items():
        if type(data[key]) is not type(expected) or data[key] != expected:
            raise ResearchError("GAO_CASEBOOK_SOURCE_SCOPE_OR_RIGHTS_TAMPERED")
    rows = data["cases"]
    if type(rows) is not list or len(rows) != len(PINNED):
        raise ResearchError("GAO_CASEBOOK_CASE_POPULATION_INVALID")
    for row, values in zip(rows, PINNED, strict=True):
        if type(row) is not dict or set(row) != set(ROW_KEYS):
            raise ResearchError("GAO_CASEBOOK_CASE_SCHEMA_INVALID")
        expected = dict(zip(ROW_KEYS, values, strict=True))
        if any(type(row[key]) is not type(value) or row[key] != value
               for key, value in expected.items()):
            raise ResearchError("GAO_CASEBOOK_HISTORICAL_FACT_OR_DISPOSITION_TAMPERED")
        if (row["reported_gsa_audited_charge_cents"] is not None
                and row["reported_carrier_collected_cents"]
                    - row["reported_gsa_audited_charge_cents"]
                    != row["reported_gsa_deducted_cents"]):
            raise ResearchError("GAO_CASEBOOK_ARITHMETIC_INVALID")
        if not row["official_url"].startswith("https://www.gao.gov/products/"):
            raise ResearchError("GAO_CASEBOOK_NONOFFICIAL_SOURCE")
    sustained = [x for x in rows if x["disposition"] == SUSTAINED]
    invalid = [x for x in rows if x["disposition"] == INVALID]
    if (len(sustained) != 3 or len(invalid) != 1
            or sum(x["reported_gsa_deducted_cents"] for x in sustained) != 319169
            or sum(x["reported_gsa_deducted_cents"] for x in invalid) != 22075):
        raise ResearchError("GAO_CASEBOOK_AGGREGATE_OR_NEGATIVE_CONTROL_INVALID")
    return data


def load_casebook(path: Path = FIXTURE) -> dict:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ResearchError("GAO_CASEBOOK_SOURCE_MISSING_OR_INVALID") from exc
    return validate_casebook(row)


def build_receipt(*, as_of: date | None = None, fixture: dict | None = None) -> dict:
    observed = as_of if as_of is not None else datetime.now(timezone.utc).date()
    if (type(observed) is not date or observed < date(2026, 10, 26)
            or observed > datetime.now(timezone.utc).date()):
        raise ResearchError("GAO_CASEBOOK_RECEIPT_DATE_INVALID")
    source = load_casebook() if fixture is None else validate_casebook(fixture)
    upheld = [x for x in source["cases"] if x["disposition"] == SUSTAINED]
    reversed_cases = [x for x in source["cases"] if x["disposition"] == INVALID]
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "observed_at_utc_date": observed.isoformat(),
        "decision_count": len(source["cases"]),
        "independently_reviewed_government_adjudication_cases": len(source["cases"]),
        "upheld_gsa_setoff_cases": len(upheld),
        "upheld_reported_setoff_cents_historical_only": sum(
            x["reported_gsa_deducted_cents"] for x in upheld),
        "invalidated_gsa_setoff_cases": len(reversed_cases),
        "invalidated_reported_setoff_cents_not_overcharges": sum(
            x["reported_gsa_deducted_cents"] for x in reversed_cases),
        "decision_labels": [
            {"case_id": row["case_id"], "decision_date": row["decision_date"],
             "official_url": row["official_url"],
             "historical_gao_disposition": row["disposition"],
             "reported_gsa_setoff_cents": row["reported_gsa_deducted_cents"],
             "independent_original_invoice_custody_verified": False,
             "modern_customer_scoring_allowed": False}
            for row in source["cases"]
        ],
        "authored_casebook_sha256_not_publisher_source_bytes": digest(source),
        "publisher_html_sha256": None,
        "original_invoice_tariff_and_bank_proofs_verified": 0,
        "independent_modern_customer_error_labels": 0,
        "verified_retally_recovered_cash_cents": 0,
        "commercial_use_authorized": False,
        "customer_contact_actions": 0,
        "production_engine_changes": 0,
        "limitations": (
            "GAO independent decision review is historical adjudication only. "
            "Original invoices, tariff exhibits, and separate bank settlements "
            "were not obtained. B-189100 audited net is derivable from paid minus "
            "deduction but NOT printed as an independently verified rate. "
            "B-221594 reverses a GSA deduction and is NOT an overcharge. "
            "No RETALLY customers, refunds, or contemporary rate authority."
        ),
    }
    return {**body, "receipt_sha256": digest(body)}


def verify_receipt(receipt: object, *, fixture: dict | None = None) -> dict:
    if type(receipt) is not dict:
        raise ResearchError("GAO_CASEBOOK_RECEIPT_INVALID")
    try:
        day = date.fromisoformat(receipt["observed_at_utc_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ResearchError("GAO_CASEBOOK_RECEIPT_DATE_INVALID") from exc
    expected = build_receipt(as_of=day, fixture=fixture)
    if receipt != expected or set(receipt) != set(expected):
        raise ResearchError("GAO_CASEBOOK_RECEIPT_FORGED_OR_STALE")
    return expected


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--verify", action="store_true")
    args = cli.parse_args()
    if args.verify:
        if args.output is None:
            raise SystemExit("--verify requires --output")
        try:
            report = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ResearchError("GAO_CASEBOOK_RECEIPT_MISSING_OR_INVALID") from exc
        result = verify_receipt(report)
    else:
        result = build_receipt()
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                                   encoding="utf-8")
    print(json.dumps({
        "historical_adjudication_cases": result["decision_count"],
        "upheld_setoffs_cents": result["upheld_reported_setoff_cents_historical_only"],
        "invalidated_setoffs_cents": result["invalidated_reported_setoff_cents_not_overcharges"],
        "independent_modern_customer_error_labels": 0,
        "verified_retally_recovered_cash_cents": 0,
        "verified": args.verify,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
