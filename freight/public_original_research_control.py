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
from freight.public_gsa_false_positive_payment_v1 import report as gsa_false_positive_refund
from freight.public_sec_contract_authority_v1 import report as original_sec_contract_report
from freight.public_crowley_court_money_lineage_v1 import report as original_court_money_lineage

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
    gsa=gsa_false_positive_refund()
    sec=original_sec_contract_report()
    crowley=original_court_money_lineage()

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
        and sec["independently_published_original_SEC_agreements"]==2
        and sec["NEDAK_2007_published_rate_rows"]==7
        and sec["SWIFT_2005_selected_fuel_bands"]==7
        and sec["historical_governing_index_methods"]=={
            "NEDAK_WESTERN_2007":"LOCAL_NONAFFILIATED_NO2_DIESEL_RETAIL_O_NEILL_NE",
            "SWIFT_LOAD_SOURCE_2005":"DOE_NATIONAL_AVERAGE_DIESEL_MON_OR_FEDERAL_HOLIDAY_TUE",
        }
        and sec["NEDAK_illustration_not_actual_invoice"]["hypothetical_unamended_freight_charge_usd"]=="13.29"
        and sec["SWIFT_illustration_not_actual_invoice"]["hypothetical_FUEL_ONLY_charge_usd"]=="1.50"
        and sec["current_signed_amendments_and_invoices_unverified"] is True
        and sec["2026_EIA_prices_not_approved_for_2007_local_index"] is True
        and sec["actual_RETALLY_customer_invoices"]==0
        and sec["actual_RETALLY_overcharge_cents"] is None
        and sec["actual_RETALLY_recovery_cents"]==0
        and sec["commercial_claim_clearance"]=="NO_GO"
        and crowley["source_documents"]==3
        and crowley["source_timeline_events"]==4
        and crowley["GSA_FY2023_reported_vendor_refund_approx_cents"]==2960000000
        and crowley["GSA_FY2023_reported_vendor_refund_approx_cents"]==
              gsa["publisher_reported_vendor_payment_approx_cents"]
        and crowley["2023_DFTS_29_6m_refund_promise_and_GSA_paid_report_same_money"] is True
        and crowley["must_not_double_count_29_6m_as_59_2m"] is True
        and crowley["GSA_FY2023_bank_transfer_receipt_independently_authenticated"] is False
        and crowley["2023_separate_Ocean_USC9_refund_only_promised_cents"]==3584043
        and crowley["2023_Ocean_USC9_bank_payment_verified"] is False
        and crowley["2025_11_8m_Claims_Court_damages_claim_cents"]==1180000000
        and crowley["2025_11_8m_claim_was_awarded_or_paid_by_appeal"] is False
        and crowley["current_2026_parallel_docket_resolution"] is None
        and crowley["DCCircuit_2025_limited_GSA_audit_to_carriers_and_freight_forwarders"] is True
        and crowley["private_RETALLY_can_issue_statutory_GSA_offsets"] is False
        and crowley["RETALLY_customer_invoices_ever_verified"]==0
        and crowley["RETALLY_customer_cash_recovered_cents"]==0
        and crowley["commercial_claim_clearance"]=="NO_GO"
    ):
        _reject("INVALID_CUSTOMER_CLAIM_OR_SOURCE_STATUS")
    result={
        "scope":SCOPE,
        "original_public_source_record_counts":SOURCE_COUNTS,
        "total_bounded_observations":sum(observed.values()),
        "standalone_official_publisher_examples":1,
        "separate_original_SEC_historical_carrier_agreements":2,
        "SEC_contracts_not_in_307_public_observation_count":True,
        "SEC_2007_local_vs_2005_national_index_distinct":True,
        "SEC_2007_exact_source_table_rows":7,
        "SEC_2005_selected_source_fuel_bands":7,
        "SEC_no_original_customer_invoices_or_2026_contract_applicability":True,
        "separate_Crowley_GSA_2023_2025_original_source_documents":3,
        "separate_Crowley_GSA_financial_timeline_events":4,
        "court_original_2023_DFTS_refund_promise_is_same_29_6m_as_GSA_reported_payment":True,
        "court_budget_pair_not_two_independent_29_6m_payments":True,
        "court_separate_Ocean_USC9_refund_35840_43_PROMISE_NOT_PAID":True,
        "court_11_8m_claim_as_of_2025_NOT_AN_APPELLATE_AWARD_OR_PAID":True,
        "court_private_statutory_setoff_right_for_RETALLY":False,
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
        "separate_GSA_false_positive_correction_public_report_records":1,
        "GSA_historical_FY2023_VENDOR_REPAYMENT_approx_cents":2960000000,
        "GSA_payment_direction_government_to_vendor_NOT_RETALLY":True,
        "GSA_potential_additional_11_8m_vendor_repayment_UNVERIFIED":True,
        "government_NOCs_may_be_erroneous_and_collections_reversed":True,
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
        "were independently inspected. Two SEC-filed historical motor-carrier "
        "agreements have different local versus federal diesel indexes and "
        "neither supplies current customer invoices. Original federal court "
        "and GSA financial reports refer to the SAME $29.6 million repayment "
        "at different stages, never two separate cash receipts; $11.8 million "
        "claimed in the 2025 appeal was not a money award. "
        "A separate GSA report documents "
        "a vendor repayment following ERRONEOUS notices of overcharge. Neither "
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
