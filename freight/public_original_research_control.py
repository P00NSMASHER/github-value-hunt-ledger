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
        and gao["historical_distinct_decisions"]==6
        and gao["gao_reported_collection_events"]==7
        and gao["agency_reported_collection_modes"]=={
            "CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT":2,
            "GOVERNMENT_APPLIED_SET_OFF":5,
        }
        and gao["cases_with_uncollected_future_deduction"]==1
        and gao["cases_with_carrier_refund_authorized_but_unverified_paid"]==1
        and gao["source_transcribed_historical_collection_report_not_payment_bank_proof"] is True
        and gao["actual_carrier_account_bank_or_Treasury_posting_independently_verified"] is False
        and gao["final_unreversed_net_government_recovery_total_cents"] is None
        and gao["real_RETALLY_customer_invoices_examined"]==0
        and gao["real_RETALLY_customer_recoveries_cents"]==0
        and gao["commercial_claim_clearance"]=="NO_GO"
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
        "confirmed paid. Six distinct GAO government historical case decisions "
        "describe collected offsets/refunds, but no original bank/Treasury postings "
        "were independently inspected. None is RETALLY revenue.</p>"
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
