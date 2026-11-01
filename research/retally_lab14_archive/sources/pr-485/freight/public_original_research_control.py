"""RETALLY Lab 14 read-only public-source audit census.

Separates publisher facts, modeled estimates, bounded microdata prefixes,
carrier schedules and administrative payment orders. None constitutes a
RETALLY customer invoice, contractual error or recovered cash.

This module never performs network I/O, writes recovery data, obtains keys,
sends emails, schedules tasks or changes production code.
"""
from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path

from freight.public_faf6_eia_v1 import public_context_report
from freight.public_carrier_schedules_v1 import public_schedule_report
from freight.public_cfs2022_prefix_v1 import report as cfs_prefix
from freight.public_stb_waybill_prefix_v1 import report as stb_prefix
from freight.public_cfs2022_official_example_v1 import verified_published_example
from freight.public_fmc_adjudication_v1 import verified_public_order
from freight.public_gao_historical_collection_v1 import public_collection_report
from freight.public_gao_b261127_contract_counterexample import compare_opposite_contract_interpretations
from freight.public_gao_b186603_wrong_bol_origin import verified_original_gao_origin_decision
from freight.public_gsa_false_positive_payment_v1 import report as gsa_false_positive_refund
from freight.public_gao_setoff_reversal_v1 import verified_historical_reversal
from freight.public_gsa_transport_audit_fund_v1 import verified_accounting as gsa_fund_accounting
from freight.public_crowley_appeal_scope_v1 import report as crowley_appellate_scope

SOURCE_COUNTS={
    "BTS_FAF6_MODELED_GOODS_FLOWS":78,
    "EIA_FUEL_RETAIL_OBSERVATIONS":18,
    "CARRIER_POSTED_SURCHARGE_FACTS":11,
    "CENSUS_PUMS_ORIGINAL_PREFIX":100,
    "STB_WAYBILL_ORIGINAL_PREFIX":100,
}
SCOPE="RETALLY_EXISTING_LAB14_PUBLIC_SOURCE_CENSUS_RESEARCH_ONLY"


def _reject(reason: str) -> None:
    raise ValueError("LAB14_PUBLIC_EVIDENCE_"+reason)


def snapshot() -> dict:
    faf=public_context_report()
    carrier=public_schedule_report()
    cfs=cfs_prefix()
    stb=stb_prefix()
    maryland=verified_published_example()
    fmc=verified_public_order()
    gao=public_collection_report()
    contract_counterexample=compare_opposite_contract_interpretations()
    bol_origin_case=verified_original_gao_origin_decision()
    gsa=gsa_false_positive_refund()
    reversal=verified_historical_reversal()
    fund=gsa_fund_accounting()
    appellate=crowley_appellate_scope()

    observed={
        "BTS_FAF6_MODELED_GOODS_FLOWS":faf["faf6_source_rows_in_snapshot"],
        "EIA_FUEL_RETAIL_OBSERVATIONS":faf["eia_observations"],
        "CARRIER_POSTED_SURCHARGE_FACTS":carrier["source_rows"],
        "CENSUS_PUMS_ORIGINAL_PREFIX":cfs["sample_rows"],
        "STB_WAYBILL_ORIGINAL_PREFIX":stb["original_public_records"],
    }
    if observed!=SOURCE_COUNTS:
        _reject("SOURCE_COUNTS_OR_COVERAGE_CHANGED")
    if not (
        faf["real_invoices_or_tariffs_examined"] is False
        and faf["verified_overcharge_cents"] is None
        and faf["validated_customer_recovery_cents"]==0
        and carrier["customer_agreement_still_controls"] is True
        and carrier["verified_customer_invoice_count"]==0
        and carrier["verified_overcharge_cents"] is None
        and carrier["financial_recovery_authorized"] is False
        and cfs["national_estimate_authorized"] is False
        and cfs["actual_original_full_source_record_count_verified"] is False
        and cfs["sample_not_representative_or_weighted"] is True
        and cfs["validated_invoice_count"]==0
        and cfs["verified_recoveries_cents"]==0
        and stb["source_archive_fully_verified"] is False
        and stb["revenue_may_be_masked"] is True
        and stb["waybill_year_histogram"]=={
            "2018":14,"2020":1,"2021":20,"2022":65}
        and stb["accounting_year_histogram"]=={"2024":100}
        and stb["2024_accounting_year_not_equal_2024_shipment_year"] is True
        and stb["real_customer_invoice_count"]==0
        and stb["real_recovery_cents"]==0
        and maryland["100_prefix_rows_used_to_make_estimate"] is False
        and maryland["census_published_weighted_goods_value_usd"]=="198598788295"
        and maryland["census_published_gvf_cv_percent"]=="9.74"
        and maryland["country_or_route_total_freight_spend"] is None
        and fmc["documented_final_reparations_order_cents"]==965451
        and fmc["actual_payment_verified_cents"] is None
        and fmc["claimant_bank_or_payment_receipt_confirmed"] is False
        and fmc["retally_validated_recovery_cents"]==0
        and gao["historical_distinct_decisions"]==7
        and gao["gao_reported_collection_events"]==9
        and gao["agency_reported_collection_modes"]=={
            "CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT":3,
            "GOVERNMENT_APPLIED_SET_OFF":6,
        }
        and gao["cases_with_uncollected_future_deduction"]==1
        and gao["cases_with_carrier_refund_authorized_but_unverified_paid"]==1
        and gao["original_GAO_1980_rating_reconciled"] is True
        and gao["original_GAO_1980_one_tender_correct_charge_cents"]==617063
        and gao["original_GAO_1980_carrier_multiple_BOL_competing_charge_cents"]==671075
        and gao["original_GAO_1980_carrier_partial_refund_cents"]==110967
        and gao["original_GAO_1980_remaining_government_setoff_cents"]==54012
        and gao["original_GAO_1980_full_PDF_original_SHA_unverified"] is True
        and gao["original_GAO_1980_no_original_bill_or_tariff_scans"] is True
        and gao["source_transcribed_historical_collection_report_not_payment_bank_proof"] is True
        and gao["actual_carrier_account_bank_or_Treasury_posting_independently_verified"] is False
        and gao["final_unreversed_net_government_recovery_total_cents"] is None
        and gao["real_RETALLY_customer_invoices_examined"]==0
        and gao["real_RETALLY_customer_recoveries_cents"]==0
        and gao["commercial_claim_clearance"]=="NO_GO"
        and contract_counterexample["historical_1980_government_reported_refund_and_setoff_cents"]==164979
        and contract_counterexample["historical_1996_apparent_charge_difference_cents"]==137300
        and contract_counterexample["historical_1996_GAO_rejected_overcharge_cents"]==137300
        and contract_counterexample["historical_1996_GAO_sustained_note12_overcharge_cents"]==0
        and contract_counterexample["same_source_authority_or_tariff_in_both_cases"] is False
        and contract_counterexample["one_bill_of_lading_always_equals_a_single_chargeable_shipment"] is False
        and contract_counterexample["prebilling_government_approved_methods_must_be_reviewed"] is True
        and contract_counterexample["contract_effective_terms_must_be_independently_proven"] is True
        and contract_counterexample["verified_RETALLY_recoveries_cents"]==0
        and contract_counterexample["retally_prospect_contact_or_recovery_authorized"] is False
        and contract_counterexample["commercial_claim_clearance"]=="NO_GO"
        and bol_origin_case["original_decisions"]==1
        and bol_origin_case["distinct_GBLs_in_decision"]==2
        and bol_origin_case["carrier_government_payment_for_chairs_cents"]==39816
        and bol_origin_case["government_applied_offset_based_on_incorrect_origin_cents"]==13328
        and bol_origin_case["GAO_established_actual_origin"]=="Canton, Mississippi"
        and bol_origin_case["GAO_rebutted_BOL_presumption_with_independent_shipment_evidence"] is True
        and bol_origin_case["GAO_conditional_carrier_reimbursement_claim_cents"]==13328
        and bol_origin_case["carrier_repayment_proven_cents"] is None
        and bol_origin_case["separate_blanket_GBL_applied_setoff_cents"]==5765
        and bol_origin_case["separate_blanket_settlement_certificate_issued_cents"]==2290
        and bol_origin_case["separate_blanket_settlement_certificate_paid_verified"] is False
        and bol_origin_case["cannot_add_amounts_from_separate_shipments_as_one_recovery"] is True
        and bol_origin_case["original_BOL_scan_or_carrier_PRO_full_bytes_independently_verified"] is False
        and bol_origin_case["retally_verified_recovered_cents"]==0
        and bol_origin_case["commercial_claim_clearance"]=="NO_GO"
        and gsa["source_reports_FY2023_vendor_payment_made"] is True
        and gsa["reported_payment_FROM_government_TO_vendor"] is True
        and gsa["publisher_reported_vendor_payment_approx_cents"]==2960000000
        and gsa["possible_additional_payment_limit_cents_NOT_PROVEN"]==1180000000
        and gsa["possible_additional_payment_executed"] is False
        and gsa["notices_of_overcharge_declared_erroneous"] is True
        and gsa["is_recovered_overcharge_by_RETALLY"] is False
        and gsa["validated_RETALLY_customer_cash_cents"]==0
        and gsa["independent_vendor_bank_statement_seen"] is False
        and gsa["commercial_recovery_claim"]=="NO_GO"
        and reversal["original_decisions"]==1
        and reversal["prepetition_allowable_setoff_cents_reported"]==214759
        and reversal["postpetition_GOVERNMENT_applied_offset_LATER_DISALLOWED_cents"]==514105
        and reversal["original_offset_was_reported_executed"] is True
        and reversal["illegal_postpetition_offset_is_valid_permanent_recovery"] is False
        and reversal["GAO_said_allow_carrier_claim_if_otherwise_correct"] is True
        and reversal["independent_carrier_repayment_bank_receipt_obtained"] is False
        and reversal["government_final_net_collections_credible_cents"] is None
        and reversal["current_private_shipment_setoff_authorized"] is False
        and reversal["not_included_in_GAO_approved_historical_collection_tally"] is True
        and reversal["actual_RETALLY_cash_recovered_cents"]==0
        and reversal["commercial_claim_clearance"]=="NO_GO"
        and fund["accounting_fact_rows"]==7
        and fund["FY2023_ACTUAL_fund_receipts_thousand_USD"]==12354
        and fund["FY2024_PLAN_fund_receipts_thousand_USD"]==4168
        and fund["FY2025_PLAN_fund_receipts_thousand_USD"]==12506
        and fund["FY2023_ACTUAL_transfer_TO_suspense_thousand_USD"]==-20674
        and fund["FY2023_ACTUAL_annual_obligations_thousand_USD"]==10960
        and fund["FY2023_vendor_corrective_payment_APPROX_million_USD"]=="29.6"
        and fund["rounding_narrative_NOT_exact_transaction_voucher"] is True
        and fund["transfer_cannot_be_deducted_from_same_year_receipts_to_compute_recovery_rate"] is True
        and fund["no_customer_freight_invoice_verification"] is True
        and fund["no_independent_bank_or_Treasury_receipt"] is True
        and fund["no_actual_RETALLY_customer_cash_cents"]==0
        and fund["no_customer_recovery_performance_forecast"] is True
        and fund["commercial_claim_clearance"]=="NO_GO"
        and appellate["original_published_decisions"]==1
        and appellate["official_opinion_date"]=="2025-07-18"
        and appellate["court_reversed_lower_GSA_audit_scope_holding"] is True
        and appellate["court_remanded_for_further_proceedings"] is True
        and appellate["court_did_not_award_individual_damages"] is True
        and appellate["published_minimum_notices_of_overcharge_alleged_exceeds"]==50000
        and appellate["published_alleged_gross_amount_approx_usd"]==37000000
        and appellate["historical_notices_are_customer_errors_confirmed"] is False
        and appellate["contemporaneous_court_of_federal_claims_demand_usd_not_paid"]==11800000
        and appellate["later_litigation_or_payment_2026_outcome_verified"] is False
        and appellate["no_private_commercial_freight_setoff_authority"] is True
        and appellate["retally_real_customer_invoice_count"]==0
        and appellate["retally_recovered_cents"]==0
        and appellate["commercial_claim_clearance"]=="NO_GO"
    ):
        _reject("INVALID_CUSTOMER_CLAIM_OR_SOURCE_STATUS")
    result={
        "scope":SCOPE,
        "original_public_source_record_counts":SOURCE_COUNTS,
        "total_bounded_observations":sum(observed.values()),
        "standalone_official_publisher_examples":1,
        "standalone_external_adjudication_records":1,
        "separate_original_GAO_historical_collection_decisions":gao["historical_distinct_decisions"],
        "separate_GAO_reported_historical_collection_events":gao["gao_reported_collection_events"],
        "GAO_original_reported_refunds":gao["agency_reported_collection_modes"]["CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT"],
        "GAO_original_reported_applied_setoffs":gao["agency_reported_collection_modes"]["GOVERNMENT_APPLIED_SET_OFF"],
        "GAO_decisions_are_external_historical_not_307_source_observations":True,
        "GAO_reported_collections_not_independently_Treasury_bank_verified":True,
        "GAO_final_unreversed_net_government_recovery_total_cents":None,
        "GAO_future_uncollected_or_carrier_reimbursement_unverified":True,
        "GAO_1980_original_one_lot_vs_multiple_BOL_rate_reconciliation":True,
        "GAO_1980_one_lot_allowed_charge_cents":617063,
        "GAO_1980_multiple_BOL_carrier_rate_cents":671075,
        "GAO_1980_voluntary_carrier_refund_cents":110967,
        "GAO_1980_remainder_setoff_cents":54012,
        "GAO_1980_no_original_tariff_or_Treasury_receipt_examined":True,
        "separate_original_GAO_1996_contract_specific_carrier_upheld_decisions":1,
        "GAO_1996_same_GBL_apparent_difference_USD_CENTS_not_recoverable":137300,
        "GAO_1996_original_publication_upheld_TCN_based_billings":True,
        "GAO_1996_rejected_NOTE14_additional_terminal_charge":True,
        "GAO_1996_mathematical_invoice_variance_NOT_A_VALID_OVERCHARGE":True,
        "GAO_1980_vs_1996_CONTRACT_AUTHORITY_IS_CASE_SPECIFIC":True,
        "GAO_1996_contract_specific_entitlement_NOT_RETALLY_CASH":True,
        "separate_original_GAO_1976_wrong_BOL_origin_decisions":1,
        "GAO_1976_applied_offset_on_disproven_shipper_origin_cents":13328,
        "GAO_1976_carrier_repayment_only_conditionally_allowed":True,
        "GAO_1976_repayment_to_carrier_verified_cents":None,
        "GAO_1976_independent_shipment_origin_evidence_overrode_BOL_text":True,
        "GAO_1976_blanket_GBL_has_its_own_setoff_and_certificate":True,
        "GAO_1976_distinct_GBL_balances_must_not_be_combined":True,
        "separate_GSA_false_positive_correction_public_report_records":1,
        "GSA_historical_FY2023_VENDOR_REPAYMENT_approx_cents":2960000000,
        "GSA_payment_direction_government_to_vendor_NOT_RETALLY":True,
        "GSA_potential_additional_11_8m_vendor_repayment_UNVERIFIED":True,
        "government_NOCs_may_be_erroneous_and_collections_reversed":True,
        "separate_GAO_1979_improper_setoff_decisions":1,
        "GAO_1979_applied_but_later_disallowed_offset_cents":514105,
        "GAO_1979_reversal_reimbursement_not_verified":True,
        "GAO_1979_negative_case_not_approved_collection":True,
        "GAO_1979_private_setoff_authority_not_established":True,
        "GSA_FY2023_original_accounting_receipts_thousands_USD":12354,
        "GSA_FY2024_original_receipts_PLAN_thousands_USD":4168,
        "GSA_FY2025_original_receipts_PLAN_thousands_USD":12506,
        "GSA_FY2023_transfer_to_suspense_thousands_USD":-20674,
        "GSA_appropriation_table_rows_separately_verified":7,
        "GSA_FY2023_accounting_receipts_are_not_invoice_level_overcharge_proof":True,
        "GSA_program_receipts_cannot_establish_RETALLY_recovery_rate":True,
        "separate_2025_DC_Circuit_Crowley_original_decisions":1,
        "Crowley_2025_court_reversed_scope_to_audit_non_carrier":True,
        "Crowley_alleged_nocs_more_than":50000,
        "Crowley_alleged_aggregated_dollars_APPROX_not_proven_cents":3700000000,
        "Crowley_parallel_11_8m_damages_DEMAND_NOT_AWARD_cents":1180000000,
        "Crowley_2026_final_claim_payment_not_verified":True,
        "Crowley_federal_case_holding_not_private_RETALLY_authority":True,
        "census_official_md_origin_pums_record_count":maryland["pums_md_origin_unweighted_record_count"],
        "census_official_md_origin_weighted_GOODS_value_usd":maryland["census_published_weighted_goods_value_usd"],
        "census_official_md_origin_gvf_cv_percent":maryland["census_published_gvf_cv_percent"],
        "stb_sample_accounting_year_histogram":stb["accounting_year_histogram"],
        "stb_sample_waybill_year_histogram":stb["waybill_year_histogram"],
        "fmc_public_order_cents_not_received_funds":fmc["documented_final_reparations_order_cents"],
        "fmc_award_actual_cash_received_verified":False,
        "bts_modeled_goods_not_freight_spend":True,
        "eia_diesel_not_customer_fuel_tariff":True,
        "published_carrier_rates_not_private_terms":True,
        "census_prefix_no_population_estimates":True,
        "stb_prefix_not_2024_shipments_or_unmasked_revenue":True,
        "original_full_census_and_stb_archives_not_downloaded":True,
        "original_fmc_pdf_full_bytes_not_hashed":True,
        "source_provenance_classes_are_not_equivalent":True,
        "real_RETALLY_customer_invoices_seen":0,
        "actual_RETALLY_cash_recovered_cents":0,
        "original_historical_findings_still_open":26,
        "independent_first_customer_human_gates_unmet":18,
        "commercial_claim_clearance":"NO_GO",
    }
    canonical=json.dumps(result,sort_keys=True,separators=(",",":")).encode("utf-8")
    result["local_content_sha256"]=hashlib.sha256(canonical).hexdigest()
    result["local_hash_not_an_external_original_source_signature"]=True
    return result


def html_report(data:dict)->str:
    if data.get("scope")!=SCOPE or data.get("commercial_claim_clearance")!="NO_GO":
        _reject("UNVERIFIED_RENDERING")
    rows="".join(
        f"<tr><th>{escape(key)}</th><td>{count:,d}</td></tr>"
        for key,count in sorted(data["original_public_source_record_counts"].items())
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>RETALLY Lab 14 — public evidence census</title></head>"
        "<body><main><h1>Original public evidence — research only</h1>"
        "<p>These rows are NOT verified customer invoices, overcharges or recoveries.</p>"
        "<table><caption>Bounded source evidence, not equivalent observations</caption>"
        "<thead><tr><th>Source category</th><th>Records</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "<p>Maryland's Census-weighted goods value is a separately published "
        "worked example; the FMC award is legally ordered, not independently "
        "confirmed paid. Seven distinct GAO government historical case decisions "
        "describe collected offsets/refunds, but no original bank/Treasury postings "
        "were independently inspected. Another GAO decision found $5,141.05 "
        "of applied post-bankruptcy-petition setoffs invalid, with no proof "
        "of the carrier's repayment. A separate GSA report documents "
        "a vendor repayment following ERRONEOUS notices of overcharge. "
        "The same public FY2025 budget gives FY2023 original fund receipts and "
        "FY2024/25 PLANNED values; these are government fund accounting, not "
        "private invoice credits or recoverable amounts. An original 1996 "
        "GAO decision independently upheld a carrier charge despite a "
        "$1,373 mathematical difference, because the agency had approved "
        "the contract's TCN-based billing interpretation beforehand; "
        "no private shipper recovery is implied. An independent 1976 GAO "
        "decision rebutted the government BOL's typed Washington DC origin "
        "with factory evidence showing shipment from Canton Mississippi; "
        "the carrier's $133.28 repayment claim was allowed only if otherwise "
        "correct, with no receipt showing it was paid. A separate 2025 "
        "federal appellate decision restricted GSA authority for the "
        "particular non-carrier intermediary's bills; alleged $37M NOCs "
        "and a separate $11.8M demand are NOT validated recovery money. Neither "
        "publication establishes RETALLY revenue.</p>"
        f"<p>Source content hash: <code>{escape(data['local_content_sha256'])}</code>"
        " (local integrity only, not an external signature).</p>"
        "<p>26 historical issues open; 18 human gates unmet. "
        "Commercial/financial operations: NO-GO.</p>"
        "</main></body></html>"
    )


def main()->None:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,
                   help="Write sanitized derived JSON and HTML in a research output directory")
    args=p.parse_args()
    result=snapshot()
    if args.out:
        folder=args.out
        if folder.is_symlink() or folder.exists() and not folder.is_dir():
            _reject("UNSAFE_OUTPUT")
        folder.mkdir(parents=True,exist_ok=True)
        for name,content in (
            ("public_evidence_census.json",json.dumps(result,sort_keys=True,indent=2)+"\n"),
            ("index.html",html_report(result))
        ):
            target=folder/name
            if target.is_symlink():
                _reject("UNSAFE_OUTPUT")
            target.write_text(content,encoding="utf-8")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
