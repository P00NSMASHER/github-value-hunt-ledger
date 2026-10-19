"""GSA first-party historical *correction* of erroneous transportation audit notices.

GSA's FY2025 Congressional Justification says the agency MADE a $29.6M
payment to a DoD transportation vendor in FY2023 following erroneous
notices of overcharge. The cited possible additional $11.8M is NOT paid
or a proved debt. All values are GSA-reported approximate millions.

Neither source constitutes private customer savings or RETALLY revenue.
No external invoice, current contract, bank ledger or settlement authority.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"fixtures/public_gsa_2025_transport_audit_erroneous_nocs_payment.json"
KIND="GSA_PUBLISHER_REPORTS_2023_VOLUNTARY_VENDOR_PAYMENT_FOR_ERRONEOUS_NOTICES"
SCOPE="HISTORICAL_REAL_GOVERNMENT_CORRECTION_PAYMENT_NOT_RETALLY_RECOVERY"

PINNED={
    "schema_version":1,
    "source_publisher":"U.S. General Services Administration",
    "source_document":"GSA FY 2025 Congressional Justification — Transportation Audit Contracts and Contract Administration",
    "source_url":"https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf",
    "source_location":"Permanent Budget Authority, Transportation Audits, printed pages P-2 through P-5 (PDF pages 291-294 approximately)",
    "source_reporting_fiscal_year":2023,
    "evidence_kind":KIND,
    "original_notices_of_overcharge_issued_error_acknowledged":True,
    "amount_reported_paid_TO_DoD_transportation_vendor_cents":2960000000,
    "amount_reported_returned_from_receipts_account_approx_cents":2070000000,
    "amount_reported_paid_from_suspense_account_approx_cents":890000000,
    "potential_additional_disputed_vendor_payment_upper_bound_cents":1180000000,
    "possible_additional_vendor_payment_already_proven":False,
    "original_billing_invoices_and_contracts_independently_examined":False,
    "original_government_pdf_source_text_confirmed":True,
    "complete_PDF_bytes_sha256_independently_recorded":False,
    "separate_vendor_bank_posting_independently_inspected":False,
    "RETALLY_customer_overcharges_recovered_cents":0,
    "erroneous_notices_must_not_be_treated_as_valid_customer_savings":True,
    "financially_validated_net_overpayment_collected_from_vendor_cents":None,
    "category":SCOPE,
    "research_limitation":"First-party GSA statement establishes its accounting/reporting claim, not a separate bank-voucher audit; USD amounts are GSA-published approximate millions and do not prove every underlying invoice error.",
}


def report()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>8_000:
        raise ValueError("GSA_FALSE_POSITIVE_UNTRUSTED_SOURCE")
    try:
        raw=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("GSA_FALSE_POSITIVE_INVALID_SOURCE") from exc
    if (type(raw) is not dict or frozenset(raw)!=frozenset(PINNED)
        or any(type(raw[k]) is not type(expected) or raw[k]!=expected
               for k,expected in PINNED.items())):
        raise ValueError("GSA_FALSE_POSITIVE_ORIGINAL_REPORT_MISMATCH")
    if (raw["amount_reported_returned_from_receipts_account_approx_cents"]
        +raw["amount_reported_paid_from_suspense_account_approx_cents"]
        !=raw["amount_reported_paid_TO_DoD_transportation_vendor_cents"]):
        raise ValueError("GSA_FALSE_POSITIVE_FUNDING_MATH_FAILED")
    return {
        "scope":SCOPE,
        "original_reporting_source":"GSA FY2025 CONGRESSIONAL JUSTIFICATION",
        "source_reports_FY2023_vendor_payment_made":True,
        "publisher_reported_vendor_payment_approx_cents":2960000000,
        "reported_payment_FROM_government_TO_vendor":True,
        "possible_additional_payment_limit_cents_NOT_PROVEN":1180000000,
        "possible_additional_payment_executed":False,
        "notices_of_overcharge_declared_erroneous":True,
        "is_recovered_overcharge_by_RETALLY":False,
        "validated_RETALLY_customer_cash_cents":0,
        "independent_vendor_bank_statement_seen":False,
        "underlying_original_invoices_independently_verified":False,
        "original_source_PDF_all_bytes_hashed":False,
        "no_cross_case_aggregation_with_GAO_or_FMC":True,
        "commercial_recovery_claim":"NO_GO",
    }


if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2))
