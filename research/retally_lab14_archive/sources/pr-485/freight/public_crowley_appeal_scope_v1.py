"""RETALLY Lab 14 — authoritative 2025 federal appellate scope decision.

A court's holding about GSA statutory jurisdiction in one government
contract is NOT permission for RETALLY to act for private customers.
Historical alleged invoice NOCs and a separately asserted damages claim
are NOT actual validated freight errors or bank-confirmed repayments.

Offline, original published document metadata only; research-only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_cadc_crowley_2025_transport_audit_authority.json"

PINNED={
 "schema_version":1,
 "court":"U.S. Court of Appeals for the District of Columbia Circuit",
 "case_name":"Crowley Government Services, Inc. v. General Services Administration",
 "case_number":"23-5183",
 "majority_opinion_date":"2025-07-18",
 "official_opinion_pdf":"https://media.cadc.uscourts.gov/opinions/docs/2025/07/23-5183-2126136.pdf",
 "opinion_pages_including_dissent":56,
 "law_at_issue":"31 U.S.C. § 3726(b)",
 "majority_holding":"GSA's statutory transportation-audit authority reaches carrier/freight-forwarder bills; Crowley under the particular DFTS I contract was an intermediary and not a carrier.",
 "disposition":"DISTRICT_COURT_AUDIT_SCOPE_REVERSED_AND_REMANDED",
 "contract_specific_no_general_private_setoff_authority":True,
 "noc_first_period":"2018-08/2021",
 "original_opinion_alleged_notices_more_than":50000,
 "original_opinion_alleged_overcharge_approx_usd":37000000,
 "notices_are_allegations_not_validated_errors":True,
 "opinion_reports_three_contracting_officer_final_decisions_rejecting_contested_NOCs":True,
 "further_later_notices_over_100000_approx_boundary":True,
 "separate_court_of_federal_claims_damage_demand_usd":11800000,
 "separate_damages_litigation_referenced_in_opinion_as_unresolved":True,
 "damages_demand_current_2026_resolution_independently_checked":False,
 "damages_demand_bank_payment_received_proven":False,
 "opinion_does_not_award_11_8m_damages":True,
 "real_retally_customer_invoices_examined":0,
 "real_retally_customer_recoveries_cents":0,
 "independent_full_pdf_original_sha256_verified":False,
 "source_published_holding_is_not_retally_contract_authority":True,
 "classification":"ORIGINAL_APPELLATE_AUTHORITY_RISK_AND_UNPAID_CLAIM_NOT_RECOVERY",
}

def report()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>11_000:
        raise ValueError("CROWLEY_APPEAL_ORIGINAL_SOURCE_UNTRUSTED")
    try:
        x=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as e:
        raise ValueError("CROWLEY_APPEAL_ORIGINAL_SOURCE_INVALID_JSON") from e
    if (type(x) is not dict or frozenset(x)!=frozenset(PINNED)
        or any(type(x.get(k)) is not type(v) or x.get(k)!=v
               for k,v in PINNED.items())):
        raise ValueError("CROWLEY_APPEAL_ORIGINAL_SOURCE_FACT_MISMATCH")

    return {
        "scope":"JULY_2025_DC_CIRCUIT_CONTRACT_SPECIFIC_AUDIT_AUTHORITY",
        "official_opinion_date":"2025-07-18",
        "original_published_decisions":1,
        "court_reversed_lower_GSA_audit_scope_holding":True,
        "court_remanded_for_further_proceedings":True,
        "court_did_not_award_individual_damages":True,
        "published_minimum_notices_of_overcharge_alleged_exceeds":50000,
        "published_alleged_gross_amount_approx_usd":37000000,
        "historical_notices_are_customer_errors_confirmed":False,
        "contemporaneous_court_of_federal_claims_demand_usd_not_paid":11800000,
        "later_litigation_or_payment_2026_outcome_verified":False,
        "no_private_commercial_freight_setoff_authority":True,
        "retally_real_customer_invoice_count":0,
        "retally_recovered_cents":0,
        "no_independent_full_pdf_hash_or_bank_confirmation":True,
        "commercial_claim_clearance":"NO_GO",
    }

if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2))
