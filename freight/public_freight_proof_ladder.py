"""Three incompatible public freight proof states: GAO rate, DOJ paid, DOJ agreed.

This research-only ledger does not infer modern rate authority, invoice-specific
settlement damages, a private buyer claim, paid carrier refund, or RETALLY cash.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from freight.unified_research_lab import ResearchError, digest, safe_url

FIXTURE = Path(__file__).with_name("fixtures") / "public_freight_rate_cash_proof_v1.json"
SCOPE = "PUBLIC_HISTORICAL_GAO_ADJUDICATION_AND_DOJ_SETTLEMENT_DISCLOSURES_NOT_CUSTOMER_INVOICE_TRUTH"
ROOT = {
    "schema_version": 1,
    "fixture_id": "RETALLY_FREIGHT_PUBLIC_RATE_AND_CASH_PROOF_LADDER_V1",
    "scope": SCOPE,
    "reviewed_utc_date": "2026-10-26",
    "original_publisher_response_bytes_held": False,
    "original_invoice_bol_and_tariff_pages_in_custody": False,
    "independent_customer_shipment_rate_payment_chain_verified": False,
    "commercial_reuse_authorized_for_customer_rating": False,
    "modern_customer_invoice_ground_truth_labels": 0,
    "retally_recovered_cash_cents": 0,
}
GAO = {
    "case_id": "GAO_B_143458",
    "decision_date": "1961-03-30",
    "official_url": "https://www.gao.gov/products/b-143458",
    "carrier": "PENNSYLVANIA_TRANSFER_COMPANY",
    "carrier_bill_number_GAO_transcribed": "NC_23166",
    "government_bill_of_lading_GAO_transcribed": "AF-7611030",
    "gbl_date_GAO_reported": "1958-03-07",
    "ship_from_GAO_reported": "NEW_CASTLE_PENNSYLVANIA",
    "ship_to_GAO_reported": "MCGUIRE_AIR_FORCE_BASE_NEW_JERSEY",
    "description_GAO_reported": "EIGHT_LOOSE_AUTOMOBILE_TOWING_POLES",
    "actual_weight_lb_GAO_reported": 5744,
    "applicable_minimum_weight_lb_GAO_reported": 6000,
    "applicable_ltl_rate_cents_per_100_lb_GAO_reported": 251,
    "carrier_original_billed_and_government_paid_cents_GAO_reported": 30590,
    "GAO_allowable_charge_cents_GAO_reported": 15060,
    "GAO_overcharge_cents_adjudicated": 15530,
    "tariff_reference_GAO_reported":
        "MIDDLE_ATLANTIC_FREIGHT_TARIFF_5_F_MASTER_TARIFF_18_EXCEPTIONS_TARIFF_10_M_RULE_25_D",
    "carrier_excluded_from_rule_62_2_capacity_load_roster_GAO_adjudicated": True,
    "overcharge_disposition":
        "CERTIFICATE_OF_INDEBTEDNESS_PROPER_GAO_REFUND_DEMANDED_WITHIN_30_DAYS",
    "overpayment_refunded_as_of_decision": False,
    "subsequent_refund_or_Treasury_offset_cleared_independently_verified": False,
    "GAO_original_paid_voucher_custody_in_RETALLY": False,
    "original_governing_tariff_pages_in_RETALLY": False,
    "present_day_rate_authority": False,
}
PAID = {
    "event_id": "DOJ_MENLO_ESTES_2016",
    "published_date": "2016-05-03",
    "official_url":
        "https://www.justice.gov/usao-edca/pr/"
        "menlo-worldwide-services-inc-and-its-subcontractor-estes-pay-us-13-million-resolve",
    "payee": "UNITED_STATES_GOVERNMENT",
    "doj_reports_already_paid": True,
    "menlo_settlement_paid_cents_GOV_REPORT": 1000000000,
    "estes_settlement_paid_cents_GOV_REPORT": 300000000,
    "total_settlement_paid_cents_GOV_REPORT": 1300000000,
    "alleged_billing_mechanism":
        "AIR_FREIGHT_CHARGES_WHEN_ACTUAL_SERVICE_GROUND_AND_OTHER_DTCI_CHARGES",
    "liability_adjudicated": False,
    "precise_individual_invoice_damages_in_this_release": None,
    "raw_treasury_bank_remittance_in_custody": False,
    "retally_customer_refund_or_revenue_cents": 0,
}
AGREED = {
    "event_id": "DOJ_YRC_ROADWAY_YELLOW_2022",
    "published_date": "2022-03-14",
    "official_url":
        "https://www.justice.gov/archives/opa/pr/"
        "freight-carriers-agree-pay-685-million-resolve-allegations-knowingly-presenting-false-claims",
    "doj_statement": "DEFENDANTS_AGREED_TO_PAY_APPROXIMATELY",
    "settlement_agreed_amount_cents_APPROXIMATE": 685000000,
    "doj_reports_current_completed_payment": False,
    "actual_cash_cleared_verified_amount_cents": None,
    "alleged_billing_mechanism":
        "SELECTIVELY_CHARGE_HIGHER_REWEIGHS_AND_WITHHOLD_LOWER_REWEIGHS",
    "liability_adjudicated": False,
    "independently_verified_per_shipment_reweigh_error_labels": 0,
    "retally_customer_refund_or_revenue_cents": 0,
}
KEYS = frozenset({
    "schema_version", "scope", "public_records", "GAO_historic_case_reconstructed",
    "GAO_paid_voucher_reported_not_independent_custody",
    "GAO_historical_rate_cents_per_cwt",
    "GAO_historical_billable_weight_lb", "GAO_historical_allowable_cents",
    "GAO_historical_original_charge_cents", "GAO_historical_overcharge_cents",
    "GAO_later_refund_bank_cleared_verified", "DOJ_settlement_paid_public_report_cents",
    "DOJ_settlement_paid_original_bank_record_in_custody",
    "DOJ_settlement_paid_NOT_customer_refund_or_overcharge_amount",
    "DOJ_agreed_settlement_approximate_cents",
    "DOJ_agreed_settlement_actual_paid_cents",
    "DOJ_settlement_liability_findings_cannot_be_inferred",
    "modern_customer_independent_overcharge_labels", "modern_tariff_rights_verified",
    "independent_original_transaction_bytes_held",
    "verified_RETALLY_cash_recovered_cents",
    "author_fixture_SHA256_NOT_original_publisher_hash",
    "original_publisher_SHA256", "receipt_SHA256",
})


def assert_exact(item: object, pinned: dict, tag: str) -> None:
    if type(item) is not dict or set(item) != set(pinned):
        raise ResearchError(tag + "_SCHEMA")
    for k, v in pinned.items():
        if type(item[k]) is not type(v) or item[k] != v:
            raise ResearchError(tag + "_CHANGED_FACT")
    if "official_url" in item and safe_url(item["official_url"]) != item["official_url"]:
        raise ResearchError(tag + "_UNSAFE_ORIGIN")


def validate_fixture(obj: object) -> dict:
    if type(obj) is not dict or set(obj) != set(ROOT) | {
        "historical_tariff_case", "doj_settlement_paid", "doj_settlement_agreed"
    }:
        raise ResearchError("PUBLIC_FREIGHT_PROOF_ROOT_INVALID")
    for k, v in ROOT.items():
        if type(obj[k]) is not type(v) or obj[k] != v:
            raise ResearchError("PUBLIC_FREIGHT_PROOF_CUSTOMER_OR_RIGHTS_FORGERY")
    for section, pinned in (
        ("historical_tariff_case", GAO), ("doj_settlement_paid", PAID),
        ("doj_settlement_agreed", AGREED)
    ):
        assert_exact(obj[section], pinned, section.upper())
    g, p, a = (obj["historical_tariff_case"], obj["doj_settlement_paid"],
               obj["doj_settlement_agreed"])
    min_weight = max(g["actual_weight_lb_GAO_reported"],
                     g["applicable_minimum_weight_lb_GAO_reported"])
    if (min_weight % 100 != 0
            or g["applicable_ltl_rate_cents_per_100_lb_GAO_reported"]
                * (min_weight // 100) != g["GAO_allowable_charge_cents_GAO_reported"]
            or g["carrier_original_billed_and_government_paid_cents_GAO_reported"]
                - g["GAO_allowable_charge_cents_GAO_reported"]
                != g["GAO_overcharge_cents_adjudicated"]
            or p["menlo_settlement_paid_cents_GOV_REPORT"]
                + p["estes_settlement_paid_cents_GOV_REPORT"]
                != p["total_settlement_paid_cents_GOV_REPORT"]
            or a["actual_cash_cleared_verified_amount_cents"] is not None):
        raise ResearchError("PUBLIC_FREIGHT_PROOF_ARITHMETIC_OR_CASH_INVALID")
    return obj


def load_fixture(path: Path = FIXTURE) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ResearchError("PUBLIC_FREIGHT_PROOF_FIXTURE_UNAVAILABLE") from exc
    return validate_fixture(obj)


def make_receipt(*, fixture: dict | None = None) -> dict:
    obj = load_fixture() if fixture is None else validate_fixture(fixture)
    g, p, a = (obj["historical_tariff_case"], obj["doj_settlement_paid"],
               obj["doj_settlement_agreed"])
    out = {
        "schema_version": 1,
        "scope": SCOPE,
        "public_records": (
            {"id": g["case_id"], "source": g["official_url"],
             "proof": "INDEPENDENT_GAO_HISTORICAL_RATE_DECISION",
             "source_transaction_bytes_held": False},
            {"id": p["event_id"], "source": p["official_url"],
             "proof": "DOJ_PUBLIC_STATEMENT_GOVERNMENT_SETTLEMENT_ALREADY_PAID",
             "source_transaction_bytes_held": False},
            {"id": a["event_id"], "source": a["official_url"],
             "proof": "DOJ_PUBLIC_STATEMENT_SETTLEMENT_AGREED_APPROXIMATELY_ONLY",
             "source_transaction_bytes_held": False},
        ),
        "GAO_historic_case_reconstructed": True,
        "GAO_paid_voucher_reported_not_independent_custody": True,
        "GAO_historical_rate_cents_per_cwt":
            g["applicable_ltl_rate_cents_per_100_lb_GAO_reported"],
        "GAO_historical_billable_weight_lb": max(
            g["actual_weight_lb_GAO_reported"],
            g["applicable_minimum_weight_lb_GAO_reported"]),
        "GAO_historical_allowable_cents": g["GAO_allowable_charge_cents_GAO_reported"],
        "GAO_historical_original_charge_cents":
            g["carrier_original_billed_and_government_paid_cents_GAO_reported"],
        "GAO_historical_overcharge_cents": g["GAO_overcharge_cents_adjudicated"],
        "GAO_later_refund_bank_cleared_verified": False,
        "DOJ_settlement_paid_public_report_cents":
            p["total_settlement_paid_cents_GOV_REPORT"],
        "DOJ_settlement_paid_original_bank_record_in_custody": False,
        "DOJ_settlement_paid_NOT_customer_refund_or_overcharge_amount": True,
        "DOJ_agreed_settlement_approximate_cents":
            a["settlement_agreed_amount_cents_APPROXIMATE"],
        "DOJ_agreed_settlement_actual_paid_cents": None,
        "DOJ_settlement_liability_findings_cannot_be_inferred": True,
        "modern_customer_independent_overcharge_labels": 0,
        "modern_tariff_rights_verified": False,
        "independent_original_transaction_bytes_held": False,
        "verified_RETALLY_cash_recovered_cents": 0,
        "author_fixture_SHA256_NOT_original_publisher_hash": digest(obj),
        "original_publisher_SHA256": None,
    }
    # Native JSON is used for deterministic immutable receipt serialization.
    out["public_records"] = list(out["public_records"])
    return {**out, "receipt_SHA256": digest(out)}


def verify_receipt(obj: object) -> dict:
    if type(obj) is not dict or set(obj) != KEYS or obj != make_receipt():
        raise ResearchError("PUBLIC_FREIGHT_PROOF_RECEIPT_FORGED_OR_NOT_CURRENT")
    return obj


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--verify", action="store_true")
    args = cli.parse_args()
    if args.verify:
        if args.output is None:
            cli.error("--verify requires --output")
        try:
            obj = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ResearchError("PUBLIC_FREIGHT_PROOF_RECEIPT_UNAVAILABLE") from exc
        report = verify_receipt(obj)
    else:
        report = make_receipt()
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n",
                                   encoding="utf-8")
    print(json.dumps({
        "records": len(report["public_records"]),
        "adjudicated_historical_case_cents": report["GAO_historical_overcharge_cents"],
        "DOJ_public_paid_settlement_cents": report["DOJ_settlement_paid_public_report_cents"],
        "DOJ_agreed_only_cents_APPROXIMATE": report["DOJ_agreed_settlement_approximate_cents"],
        "customer_labels": report["modern_customer_independent_overcharge_labels"],
        "RETALLY_cash_cents": report["verified_RETALLY_cash_recovered_cents"],
        "verified": args.verify,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
