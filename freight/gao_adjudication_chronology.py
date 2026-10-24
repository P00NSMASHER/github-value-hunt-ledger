"""Research-only historical GAO legal chronology: never use an overruled 1984 outcome.

Two distinct historical tariffs and adjudications are independent reference
challenges, not modern invoice-level engine accuracy, legal advice, customer
rights, verified refunds or recoverable cash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from freight.unified_research_lab import ROOT, ResearchError, digest

FIXTURES = Path(__file__).with_name("fixtures")
B215_1984 = FIXTURES / "gao_b215958_source_v1.json"
B165_1969 = FIXTURES / "gao_b165091_source_v1.json"
OUTPUT = ROOT / "gao_authority_chronology_v1.json"
PRIMARY_1984 = "https://www.gao.gov/products/b-215958"
PRIMARY_1986 = "https://www.gao.gov/products/b-215958-2"
PRIMARY_1969 = "https://www.gao.gov/products/b-165091"
SCOPE = "PUBLIC_GAO_HISTORICAL_SUPERSESSION_ONLY_NO_INVOICE_LABELS"
DEC_1984 = date(1984, 12, 5)
DEC_1986 = date(1986, 2, 18)
DEC_1969 = date(1969, 1, 3)
LATEST_HISTORICAL = "1986_GAO_RECONSIDERATION_OVERRULED_1984_AND_SUSTAINED_GSA_AUDIT"
REFERENCES = (
    ("B-215958", DEC_1984, PRIMARY_1984, "INITIAL_1984_CARRIER_FAVORABLE"),
    ("B-215958", DEC_1986, PRIMARY_1986, "1986_RECONSIDERATION_SUSTAINED_GSA"),
    ("B-165091", DEC_1969, PRIMARY_1969, "DISTINCT_517V_17980_DEDUCTION_SUSTAINED"),
)
LIMITATIONS = [
    "The 1984 B-215958 carrier-favorable decision was explicitly overruled in 1986.",
    "Historical case decisions do not create modern tariff/customer contract rights.",
    "B-165091 used a separate 517-V tariff; it is not the 190-A sealed-vehicle case.",
    "No original invoice-by-invoice rate reconstruction, bank-cleared refund or cash recovery is shown.",
    "Research-authored manifest digests are not GAO original decision byte fingerprints.",
]
RECEIPT_FIELDS = frozenset({
    "schema_version", "scope", "observed_at_utc_date",
    "case_family", "historical_tariff", "first_decision_date",
    "first_decision_url", "first_decision_disposition",
    "reconsideration_date", "reconsideration_url",
    "subsequent_history_overruled_1984", "latest_historical_case_disposition",
    "original_gbls_in_initial_proceeding",
    "original_sealed_gbls_in_initial_proceeding",
    "unresolved_1984_remainder", "per_gbl_outcomes_independently_proven",
    "separate_contrast_case", "separate_contrast_tariff",
    "separate_contrast_adjudicated_deduction_cents",
    "separate_contrast_actual_refund_cents",
    "decision_chain_sources", "b215_1984_manifest_digest",
    "b165_1969_manifest_digest",
    "owner_commercial_reuse_attestation",
    "source_specific_commercial_rights_verified",
    "current_customer_contract_applicability_proven",
    "independent_invoice_accuracy_cases", "verified_recovered_cash_cents",
    "customer_contact_actions", "source_document_bytes_stored",
    "production_engine_changes", "limitations", "receipt_sha256",
})


def _fixture(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("GAO_CHRONOLOGY_SOURCE_FIXTURE_UNAVAILABLE") from exc
    if type(obj) is not dict or type(obj.get("manifest_sha256")) is not str:
        raise ResearchError("GAO_CHRONOLOGY_SOURCE_FIXTURE_INVALID")
    body = {k: v for k, v in obj.items() if k != "manifest_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != obj["manifest_sha256"]:
        raise ResearchError("GAO_CHRONOLOGY_MANIFEST_CHANGED")
    return obj


def validate_historical_inputs(p1984: dict, p1969: dict) -> None:
    try:
        a = p1984["source"]
        b = p1969["source"]
        summary = p1984["population"]
        b_cases = p1969["adjudications"]
        b_limits = p1969["limits"]
    except (KeyError, TypeError) as exc:
        raise ResearchError("GAO_SOURCE_CHAIN_MALFORMED") from exc
    if (a.get("case_number") != "B-215958"
            or a.get("decision_date") != DEC_1984.isoformat()
            or a.get("original_record_url") != PRIMARY_1984
            or a.get("superseding_reconsideration_url") != PRIMARY_1986
            or a.get("superseding_reconsideration_date") != DEC_1986.isoformat()
            or not "190-A" in a.get("historical_tariff", "")
            or summary.get("decision_outcome") !=
                "GAO_1984_INITIAL_REVERSAL_SUBSEQUENTLY_OVERRULED_IN_1986"
            or p1984["controls"][0].get("expected") !=
                "1984_INITIAL_FAVORABLE_RULING_NOT_FINAL_1986_WRITTEN_REQUEST_REQUIRED"
            or summary.get("challenged_government_bills_of_lading") != 55
            or summary.get("decision_reversals_with_recorded_numbered_seals") != 53
            or summary.get("remainder_cases_with_unresolved_disposition") != 2
            or summary.get("per_bill_of_lading_labels_available") is not False
            or p1984["limits"].get("independent_accuracy_scoring_permitted") is not False
            or a.get("commercial_use_of_engine_input_approved") is not False
            or b.get("case_number") != "B-165091"
            or b.get("decision_date") != DEC_1969.isoformat()
            or b.get("original_record_url") != PRIMARY_1969
            or "517-V" not in b.get("historical_tariff", "")
            or not isinstance(b_cases, list) or len(b_cases) != 2
            or b_cases[0].get("adjudicated_sustained_deduction_cents") != 17980
            or b_cases[1].get("finally_allowed_amount_cents") is not None
            or b_limits.get("independent_invoice_error_accuracy_scoring_permitted") is not False
            or b.get("commercial_use_of_engine_input_approved") is not False):
        raise ResearchError("GAO_SOURCE_CHAIN_SCOPE_OR_AUTHORITY_MISMATCH")
    if any(p.get("source_bytes_acquired") is not False
           or p.get("source_bytes_sha256") is not None
           for p in (a, b)):
        raise ResearchError("GAO_SOURCE_BYTES_NOT_ORIGIN_VERIFIED")


def ruling_as_of(case_id: str, at_date: date) -> str:
    if type(at_date) is not date:
        raise ResearchError("GAO_AS_OF_DATE_INVALID")
    if case_id == "B-215958":
        if at_date < DEC_1984:
            return "NO_GAO_DECISION_AS_OF_DATE"
        if at_date < DEC_1986:
            return "GAO_1984_INITIAL_CARRIER_FAVORABLE_ONLY"
        return LATEST_HISTORICAL
    if case_id == "B-165091":
        return ("NO_GAO_DECISION_AS_OF_DATE" if at_date < DEC_1969
                else "1969_517V_GAO_SUSTAINED_17980_DEDUCTION_DISTINCT_CASE")
    raise ResearchError("GAO_UNKNOWN_CASE")


def make_receipt(at_date: date, *,
                 p1984: dict | None = None,
                 p1969: dict | None = None) -> dict:
    if type(at_date) is not date or at_date < DEC_1986 or at_date > datetime.now(timezone.utc).date():
        raise ResearchError("GAO_RECEIPT_DATE_INVALID")
    a = p1984 or _fixture(B215_1984)
    b = p1969 or _fixture(B165_1969)
    validate_historical_inputs(a, b)
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "observed_at_utc_date": at_date.isoformat(),
        "case_family": "B-215958",
        "historical_tariff": "NASI_RULES_TARIFF_190_A_ITEM_470_B_C",
        "first_decision_date": DEC_1984.isoformat(),
        "first_decision_url": PRIMARY_1984,
        "first_decision_disposition": "GAO_1984_CARRIER_FAVORABLE_INITIAL_ONLY",
        "reconsideration_date": DEC_1986.isoformat(),
        "reconsideration_url": PRIMARY_1986,
        "subsequent_history_overruled_1984": True,
        "latest_historical_case_disposition": ruling_as_of("B-215958", at_date),
        "original_gbls_in_initial_proceeding": 55,
        "original_sealed_gbls_in_initial_proceeding": 53,
        "unresolved_1984_remainder": 2,
        "per_gbl_outcomes_independently_proven": 0,
        "separate_contrast_case": "B-165091",
        "separate_contrast_tariff": "517_V_ITEM_2400",
        "separate_contrast_adjudicated_deduction_cents": 17980,
        "separate_contrast_actual_refund_cents": None,
        "decision_chain_sources": [
            {"case_number": case, "decision_date": dated.isoformat(),
             "official_url": url, "outcome_class": category}
            for case, dated, url, category in REFERENCES
        ],
        "b215_1984_manifest_digest": a["manifest_sha256"],
        "b165_1969_manifest_digest": b["manifest_sha256"],
        "owner_commercial_reuse_attestation": "OWNER_ATTESTED_NOT_SOURCE_VERIFIED",
        "source_specific_commercial_rights_verified": False,
        "current_customer_contract_applicability_proven": False,
        "independent_invoice_accuracy_cases": 0,
        "verified_recovered_cash_cents": 0,
        "customer_contact_actions": 0,
        "source_document_bytes_stored": 0,
        "production_engine_changes": 0,
        "limitations": list(LIMITATIONS),
    }
    return {**body, "receipt_sha256": digest(body)}


def validate_receipt(doc: dict, *, at_date: date | None = None) -> dict:
    at_date = at_date or datetime.now(timezone.utc).date()
    if type(doc) is not dict or frozenset(doc) != RECEIPT_FIELDS:
        raise ResearchError("GAO_CHRONOLOGY_RECEIPT_SCHEMA_INVALID")
    try:
        observed = date.fromisoformat(doc["observed_at_utc_date"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ResearchError("GAO_CHRONOLOGY_RECEIPT_DATE_INVALID") from exc
    if observed > at_date or (at_date - observed).days > 2:
        raise ResearchError("GAO_CHRONOLOGY_RECEIPT_STALE_OR_FUTURE")
    expected = make_receipt(observed)
    if doc != expected:
        raise ResearchError("GAO_CHRONOLOGY_RECEIPT_TAMPERED")
    return doc


def run(*, output: Path = OUTPUT, verify_only: bool = False,
        at_date: date | None = None) -> dict:
    if verify_only:
        if not output.is_file():
            raise ResearchError("GAO_CHRONOLOGY_RECEIPT_MISSING")
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ResearchError("GAO_CHRONOLOGY_RECEIPT_INVALID") from exc
        validate_receipt(data, at_date=at_date)
    else:
        data = make_receipt(at_date or datetime.now(timezone.utc).date())
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        tmp.replace(output)
    return {
        "scope": SCOPE,
        "final_historical_authority": data["latest_historical_case_disposition"],
        "1984_favorable_decision_overruled": data["subsequent_history_overruled_1984"],
        "gbl_individual_labels_proven": data["per_gbl_outcomes_independently_proven"],
        "customer_cash_recovered_cents": data["verified_recovered_cash_cents"],
        "source_specific_commercial_rights_verified": False,
        "verified": verify_only,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(output=args.output, verify_only=args.verify), sort_keys=True))


if __name__ == "__main__":
    main()
