"""First-party GSA FY2025 transportation-audit fund account table.

This is a fiscal report of a government fund, NOT a verified set of
private transportation invoices or RETALLY recoveries. FY2023 actual
accounting rows differ categorically from FY2024/25 budget PLANS.

No network, bank, carrier, or production access; read-only.
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_gsa_transport_audit_fund_FY2025_report.json"
OFFICIAL="https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf"
KEYS=frozenset((
 "schema_version","original_publisher","document_name","original_url",
 "source_report_pdf_page_zero_based","source_printed_page","source_table",
 "original_source_table_unit","facts",
 "source_narrative_reported_vendor_repayment_approx_million_usd",
 "source_narrative_receipts_portion_approx_million_usd",
 "source_narrative_unallocated_suspense_portion_approx_million_usd",
 "source_receipt_transfer_exact_table_thousands_usd",
 "bookkeeping_rounding_precision_caveat",
 "receipts_are_not_individually_verified_customer_freight_overcharge_refunds",
 "reported_vendor_payment_is_refund_TO_vendor_for_erroneous_NOCs",
 "future_fiscal_year_plans_are_not_actuals",
 "independent_bank_Treasury_electronic_transfer_examined",
 "current_applicability_to_RETALLY_private_customer",
 "no_customer_invoice_or_recovered_funds"
))
EXPECTED={
 ("Special Fund Receipts",2023,"ACTUAL"):12354,
 ("Special Fund Receipts",2024,"PLAN"):4168,
 ("Special Fund Receipts",2025,"PLAN"):12506,
 ("Transfer to Suspense Fund to Pay Transportation Service Provider",2023,"ACTUAL"):-20674,
 ("Obligations, appropriated (annual)",2023,"ACTUAL"):10960,
 ("Obligations, appropriated (annual)",2024,"PLAN"):9728,
 ("Obligations, appropriated (annual)",2025,"PLAN"):11565,
}
FACT_KEYS=frozenset({"line","fiscal_year","budget_status","value_thousands_usd"})

def _fail(reason):
    raise ValueError("GSA_TRANSPORT_AUDIT_FUND_"+reason)


def verified_accounting()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>15_000:
        _fail("UNTRUSTED_SOURCE")
    try:
        data=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as e:
        raise ValueError("GSA_TRANSPORT_AUDIT_FUND_INVALID_JSON") from e
    if (
        type(data) is not dict or frozenset(data)!=KEYS
        or data["schema_version"]!=1
        or data["original_publisher"]!="U.S. General Services Administration"
        or data["original_url"]!=OFFICIAL
        or data["document_name"]!="FY2025 Congressional Justification — Permanent Budget Authority, Transportation Audit Contracts and Contract Administration"
        or data["source_report_pdf_page_zero_based"]!=293
        or data["source_printed_page"]!="P-5"
        or data["source_table"]!="Amounts Available for Obligation / Special Fund Receipts"
        or data["original_source_table_unit"]!="USD THOUSANDS"
        or type(data["facts"]) is not list or len(data["facts"])!=len(EXPECTED)
        or type(data["source_receipt_transfer_exact_table_thousands_usd"]) is not int
        or data["source_receipt_transfer_exact_table_thousands_usd"]!=-20674
        or data["receipts_are_not_individually_verified_customer_freight_overcharge_refunds"] is not True
        or data["reported_vendor_payment_is_refund_TO_vendor_for_erroneous_NOCs"] is not True
        or data["future_fiscal_year_plans_are_not_actuals"] is not True
        or data["independent_bank_Treasury_electronic_transfer_examined"] is not False
        or data["current_applicability_to_RETALLY_private_customer"]!="NOT_ESTABLISHED"
        or data["no_customer_invoice_or_recovered_funds"] is not True
        or data["bookkeeping_rounding_precision_caveat"]!="Published narrative in one decimal million USD is rounded; detailed FY2023 line is thousand USD, not a direct bank statement."
    ):
        _fail("SOURCE_AUTHORITY_OR_CLASSIFICATION_CHANGED")
    seen={}
    for row in data["facts"]:
        if type(row) is not dict or frozenset(row)!=FACT_KEYS:
            _fail("INVALID_ROW_SCHEMA")
        key=(row["line"],row["fiscal_year"],row["budget_status"])
        if (key in seen or key not in EXPECTED
            or type(row["fiscal_year"]) is not int
            or type(row["value_thousands_usd"]) is not int
            or row["value_thousands_usd"]!=EXPECTED[key]):
            _fail("FORGED_ACTUAL_PLAN_OR_CASH_AMOUNT")
        seen[key]=row["value_thousands_usd"]
    if seen!=EXPECTED:
        _fail("MISSING_GOVERNMENT_ACCOUNTING_FACT")

    try:
        main=Decimal(data["source_narrative_reported_vendor_repayment_approx_million_usd"])
        part=Decimal(data["source_narrative_receipts_portion_approx_million_usd"])
        suspense=Decimal(data["source_narrative_unallocated_suspense_portion_approx_million_usd"])
    except Exception as e:
        raise ValueError("GSA_TRANSPORT_AUDIT_FUND_INVALID_NARRATIVE_NUMERIC") from e
    if not (main==Decimal("29.6") and part==Decimal("20.7")
            and suspense==Decimal("8.9") and part+suspense==main
            and (Decimal("20.674").quantize(Decimal("0.1"),rounding=ROUND_HALF_UP)==part)):
        _fail("SOURCE_ROUNDING_OR_ACCOUNT_TRANSFER_MISMATCH")

    return {
        "scope":"GSA_FY2025_OFFICIAL_BUDGET_ACCOUNTING_REPORT_NOT_RETALLY_CASH",
        "source_document_fiscal_year":2025,
        "accounting_fact_rows":7,
        "FY2023_ACTUAL_fund_receipts_thousand_USD":12354,
        "FY2024_PLAN_fund_receipts_thousand_USD":4168,
        "FY2025_PLAN_fund_receipts_thousand_USD":12506,
        "FY2023_ACTUAL_transfer_TO_suspense_thousand_USD":-20674,
        "FY2023_ACTUAL_annual_obligations_thousand_USD":10960,
        "FY2023_vendor_corrective_payment_APPROX_million_USD":"29.6",
        "rounding_narrative_NOT_exact_transaction_voucher":True,
        "transfer_cannot_be_deducted_from_same_year_receipts_to_compute_recovery_rate":True,
        "no_customer_freight_invoice_verification":True,
        "no_independent_bank_or_Treasury_receipt":True,
        "no_actual_RETALLY_customer_cash_cents":0,
        "no_customer_recovery_performance_forecast":True,
        "commercial_claim_clearance":"NO_GO"
    }

if __name__=="__main__":
    print(json.dumps(verified_accounting(),sort_keys=True,indent=2))
