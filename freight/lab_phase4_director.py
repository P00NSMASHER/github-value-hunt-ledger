"""Phase 4 bounded synchronous Experiment Director, operating only on synthetic fixtures.

Executes all 14 mapped *existing* Python research/domain functions. Does not
execute hosted Floot handlers; source ownership and bank proof remain synthetic.
No networking, carriers, payments, customer records, or background schedules.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from time import perf_counter_ns
import copy
import json

from freight.lab_assurance import digest
from freight.lab_phase3_integration import execute_domain_chain
from freight.lab_phase3_simulated_pilot import simulated_cohort
from freight.lab_phase3_economics import analyze_contingency, ContingencyAssumptions

ROOT = Path(__file__).parent
LAB_LABELS = {
    1:"Rate actual invoice",2:"Customer lifecycle simulation",
    3:"Blind synthetic accuracy",4:"Source binding",
    5:"Claims-to-cash",6:"Security-readiness controls",
    7:"Free-audit qualification",8:"Contingency economics",
    9:"Buyer procurement readiness",10:"Historical tariff authority",
    11:"Reliability/tamper recovery",12:"Payment/fraud benchmark",
    13:"Savings and negative economics",14:"Competitor evidence freshness",
}
BASE_FIVE = {1,4,5,8,11}
EXTENSIONS = {2,3,6,7,9,10,12,13,14}


def _read(path: str) -> dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))


def _must(condition: bool, failure: str) -> None:
    if not condition:
        raise ValueError(failure)


def _run_extension(lab: int, *, record, authority_book, assumptions) -> tuple[dict, str]:
    """One real existing implementation plus a separate deliberately bad input."""
    if lab == 2:
        from freight.lab_customer_scenarios import CustomerPersona, simulate_customer_reactions
        from freight.lab_operations_intelligence import JourneyEvent
        events = (
            JourneyEvent("contact-1","CUSTOMER_UPDATED","2026-10-01T00:00:00Z",
                         "SIM-BUYER","SIM-BU","INV-100","a"*64,"claim-1",("notice-1",)),
            JourneyEvent("credit-1","CREDIT_ALLOCATED","2026-10-04T00:00:00Z",
                         "SIM-BUYER","SIM-BU","INV-100","a"*64,"claim-1",("credit-evidence-1",)),
        )
        person=CustomerPersona("controller",7,3,True)
        result=simulate_customer_reactions(events,person,refund_due_cents=0,as_of="2026-10-15T00:00:00Z")
        _must(any(x["kind"]=="REQUEST_STATUS_UPDATE" for x in result["reactions"]),"NO_DELAY_RESPONSE")
        try:
            simulate_customer_reactions(events,person,refund_due_cents=-1,as_of="2026-10-15T00:00:00Z")
        except ValueError:
            pass
        else:
            raise ValueError("NEGATIVE_REFUND_ACCEPTED")
        return {"synthetic_customer_reactions":len(result["reactions"]), "receipt":result["receipt_hash"]},"NEGATIVE_REFUND_REJECTED"
    if lab == 3:
        from freight.accuracy_benchmark import load_fixture, build_accuracy_report, validate_accuracy_report
        fixture=load_fixture(ROOT/"fixtures/phase3_accuracy_gold_v1.json")
        report=build_accuracy_report(fixture)
        validate_accuracy_report(report)
        try:
            validate_accuracy_report(replace(report,rating={**report.rating,"false_positive":1}))
        except (ValueError, AssertionError):
            pass
        else:
            raise ValueError("ALTERED_ACCURACY_REPORT_ACCEPTED")
        return {"fixture":"SYNTHETIC_CODE_ADJACENT_GOLD","report_sha256":digest(asdict(report))},"REPORT_VERSION_TAMPER_REJECTED"
    if lab == 6:
        from freight.security_readiness import validate_security_readiness
        evidence=_read("PHASE3_SECURITY_READINESS_2026-10-07.json")
        errors=validate_security_readiness(evidence)
        _must(not errors,"SECURITY_BASELINE_INVALID:"+",".join(errors[:3]))
        bad=copy.deepcopy(evidence)
        bad["controls"]["authentication"]["state"]="PROVEN"
        bad["controls"]["authentication"].setdefault("facts",{})["secure_cookie"]=False
        _must(bool(validate_security_readiness(bad)),"INSECURE_COOKIE_ACCEPTED")
        return {"validated_controls":len(evidence["controls"]),"external_security_assurance":"NOT_PROVEN"},"BAD_SESSION_COOKIE_REJECTED"
    if lab == 7:
        from freight.lead_qualification import AuditLeadProfile,qualify_free_audit
        p=AuditLeadProfile(6_000_000,1100,3000,12,4,2,True,True,True,True,False,True)
        decision=qualify_free_audit(p)
        _must(decision.state.value in {"QUALIFIED","HIGH_PRIORITY_RECOVERY_CANDIDATE"},"GOOD_LEAD_REJECTED")
        try:
            AuditLeadProfile(-1,1100,3000,12,4,2,True,True,True,True)
        except ValueError:
            pass
        else:
            raise ValueError("NEGATIVE_FREIGHT_SPEND_ACCEPTED")
        return {"decision":decision.state.value,"reasons":list(decision.reasons)},"NEGATIVE_SPEND_REJECTED"
    if lab == 9:
        from freight.readiness import assess_readiness,from_dict,ReadinessStatus
        baseline=_read("fixtures/readiness_ready.json")
        inputs=from_dict(baseline)
        assessment=assess_readiness(inputs)
        blocked=assess_readiness(replace(inputs,authorization_documented=False))
        _must(blocked.status==ReadinessStatus.BLOCKED,"MISSING_BUYER_AUTH_ACCEPTED")
        return {"readiness":assessment.status.value,"score":assessment.score,
                "external_procurement_certification":"NOT_ESTABLISHED"},"MISSING_BUYER_AUTH_REJECTED"
    if lab == 10:
        from freight.rate_authority import verify_compiled_authority
        auth=authority_book.authorities[0]
        verify_compiled_authority(auth)
        try:
            verify_compiled_authority(replace(auth,authority_hash="0"*64))
        except ValueError:
            pass
        else:
            raise ValueError("MUTATED_TARIFF_ACCEPTED")
        return {"authority_hash":auth.authority_hash,"effective_from":auth.effective_from,
                "source_authenticity":"SYNTHETIC_HUMAN_REVIEW_FLAG"},"ALTERED_TARIFF_HASH_REJECTED"
    if lab == 12:
        from freight.accuracy_benchmark import load_fixture, evaluate_payments
        fixture=load_fixture(ROOT/"fixtures/phase3_accuracy_gold_v1.json")
        report, traces, total = evaluate_payments(fixture)
        _must(total>0 and 0<=traces<=total,"NO_REAL_PAYMENT_FIXTURE_EVALUATION")
        # Independent source/historical event contracts enforce validity. A
        # false positive ground-truth assertion should fail on metadata bounds.
        from freight.payment_orchestration import prepare_payment_instruction
        try:
            prepare_payment_instruction(instruction_id="invalid",buyer_id="buyer",business_unit="bu",
               payer_id="payer",payee_id="payee",currency="USD",amount_cents=-1,
               purpose="TEST",finding_proof_hashes=("a"*64,),idempotency_key="one")
        except ValueError:
            pass
        else:
            raise ValueError("NEGATIVE_PAYMENT_ACCEPTED")
        return {"evaluated_payment_cases":total,"source":"FROZEN_SYNTHETIC_GOLD",
                "outcome_digest":digest(report)},"NEGATIVE_INSTRUCTION_AMOUNT_REJECTED"
    if lab == 13:
        current=analyze_contingency(assumptions)
        worse=analyze_contingency(replace(assumptions,free_audit_minutes=assumptions.free_audit_minutes+600))
        _must(worse.expected_net_margin_cents < current.expected_net_margin_cents,
              "MORE_ANALYST_WORK_DID_NOT_LOWER_PROFIT")
        return {"modeled_margin_cents":current.expected_net_margin_cents,
                "downside_margin_cents":worse.expected_net_margin_cents,
                "actual_customer_margin_cents":None},"DOWNWARD_SENSITIVITY_PRESERVED"
    if lab == 14:
        from freight.competitive_matrix import validate_competitor_evidence
        evidence=_read("PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json")
        today=date.today()  # Old vendor snapshot must eventually expire, not become evergreen.
        issues=validate_competitor_evidence(evidence,as_of=today)
        _must(not issues,"COMPETITOR_BASELINE_INVALID:"+",".join(issues[:3]))
        bad=copy.deepcopy(evidence);bad["valid_until"]="2025-01-01"
        _must(bool(validate_competitor_evidence(bad,as_of=today)),"STALE_CLAIMS_ACCEPTED")
        from freight.research_intelligence import compile_brief
        from freight.research_public_campaign import campaign_brief, campaign_registry
        brief=campaign_brief(as_of=today)
        _must(len(brief["lanes"])==8,"INCOMPLETE_RESEARCH_DISCIPLINES")
        _must(all(x["sourced_observations"]>0 for x in brief["lanes"]),
              "RESEARCH_LANE_HAS_NO_SOURCE_LINKED_OBSERVATION")
        _must(brief["opposition_findings"]>=5,"NO_REAL_SELF_OPPOSITION")
        _must("retally:pricing:clarity" in brief["contested_issues"],
              "MISSING_PRICING_ADVERSARIAL_REVIEW")
        _must(all(not x["can_publish_as_verified"] for x in brief["prioritized_findings"]),
              "UNVERIFIED_VENDOR_RESEARCH_PROMOTED")
        registry=campaign_registry(as_of=today)
        registry["sources"][-1]["excerpt_sha256"]="0"*64
        try:
            compile_brief(registry,as_of=today)
        except ValueError:
            pass
        else:
            raise ValueError("TAMPERED_PUBLIC_SOURCE_ACCEPTED")
        from freight.research_evidence_gate import run_mission, validate_anchor_book
        proof,opposition=run_mission(as_of=today)
        _must(proof["anchor_count"]==14,"INCOMPLETE_SOURCE_ANCHOR_REVIEW")
        _must(proof["anchored_claim_count"]>=18,"CLAIM_ANCHOR_COVERAGE_REGRESSION")
        response_review=next(
            a for a in proof["assessments"]
            if a["claim_id"]=="campaign.carrier.response"
        )
        _must(response_review["review_status"]=="CURRENT_ECFR_TEXT_OBSERVED_LEGAL_REVIEW_PENDING",
              "CURRENT_PRIMARY_DISPOSITION_AUTHORITY_MISSING")
        _must(response_review["client_specific_legal_applicability_established"] is False,
              "PUBLISHED_RULE_TEXT_WRONGLY_CERTIFIED_FOR_CUSTOMER")
        _must(len(opposition["decisions"])==6,"INCOMPLETE_OPPOSITION_DECISIONS")
        _must(all(not x["public_marketing_permitted"] for x in proof["assessments"]),
              "UNREVIEWED_RESEARCH_PROMOTED_TO_MARKETING")
        if today<date(2026,12,12):
            _must(any(x["review_status"]=="FUTURE_EFFECTIVE_RULE_HOLD"
                      for x in proof["assessments"]),"FUTURE_CLASSIFICATION_ACCEPTED")
        forged=_read("research/SOURCE_ANCHORS_20261010.json")
        forged["anchors"][0]["quote"]+=" FORGED"
        _must(bool(validate_anchor_book(forged,registry,as_of=today)),
              "TAMPERED_EXTERNAL_SOURCE_QUOTE_ACCEPTED")
        from freight.research_change_impact import build_refresh_queue
        queue=build_refresh_queue(
            registry=registry, proof=proof, decisions=opposition, as_of=today
        )
        _must(queue["source_count"]>=12,"RESEARCH_SOURCE_CENSUS_INCOMPLETE")
        _must(queue["automatic_fetch_or_schedule"] is False,"UNAPPROVED_AUTOMATIC_RESEARCH")
        _must(not queue["any_sources_independently_fact_checked"],
              "SOURCE_FRESHNESS_MISLABELED_AS_FACT_CHECKING")
        from freight.research_validation_protocols import (
            build_protocol_report, validate_protocols,
        )
        validation=build_protocol_report(as_of=today, decisions=opposition)
        _must(validation["protocol_count"]==6,"MISSING_STUDY_DESIGN_COVERAGE")
        _must(validation["observed_customer_outcomes"]==0,
              "UNVERIFIED_CUSTOMER_EXPERIMENT_PROMOTED")
        _must(all(not x["can_publish_customer_results"]
                  for x in validation["protocols"]),"UNAPPROVED_STUDY_PUBLICATION")
        forged_protocols=_read("research/VALIDATION_PROTOCOLS_20261010.json")
        forged_protocols["experiments"][0]["observed_sample_count"]=99
        _must(bool(validate_protocols(forged_protocols, opposition, as_of=today)),
              "FAKE_STUDY_OUTCOME_ACCEPTED")
        from freight.research_rehearsal import run_rehearsal, validate_fixture_book
        rehearsal=run_rehearsal(as_of=today, protocol_report=validation)
        _must(rehearsal["rehearsed_protocols"]==6,"SYNTHETIC_RESEARCH_METHOD_MISSING")
        _must(rehearsal["external_studies_executed"]==0,
              "SYNTHETIC_RESEARCH_PROMOTED_TO_EXTERNAL_STUDY")
        _must(not rehearsal["verified_business_results"],
              "INVENTED_CASE_PROMOTED_AS_REAL_RECOVERY")
        adversarial=_read("research/SYNTHETIC_REHEARSALS_20261010.json")
        adversarial["cases"][0]["adjudication"]="CLAIM_VERIFIED_BY_CUSTOMER"
        _must(bool(validate_fixture_book(adversarial,validation,as_of=today)),
              "FORGED_INDEPENDENT_ADJUDICATION_ACCEPTED")
        from freight.research_data_readiness import build_readiness, validate_catalog
        sources=build_readiness(as_of=today, protocols=validation)
        _must(sources["source_leads"]==7,"PUBLIC_FREIGHT_SOURCE_REGISTRY_INCOMPLETE")
        _must(sources["datasets_imported"]==0,"PUBLIC_METADATA_FRAUDULENTLY_IMPORTED")
        _must(sources["invoice_ground_truth_benchmarks"]==0,
              "FREIGHT_MARKET_DATA_MASQUERADING_AS_INVOICE_GROUND_TRUTH")
        _must(sources["lineage_family_counts"]["CFS_FAF_2022_INTERDEPENDENT"]==4,
              "DUPLICATE_SOURCE_LINEAGE_NOT_DECLARED")
        forged_source=_read("research/PUBLIC_FREIGHT_DATA_CANDIDATES_20261010.json")
        forged_source["sources"][0]["independent_invoice_ground_truth_present"]=True
        _must(bool(validate_catalog(forged_source,validation,as_of=today)),
              "FORGED_PUBLIC_INVOICE_GROUND_TRUTH_ACCEPTED")
        from freight.research_ground_truth import (
            invented_fixture_book, validate_fixtures, run_ground_truth,
        )
        truth=run_ground_truth(as_of=today,protocols=validation)
        _must(truth["case_count"]==10,"INVOICE_REFERENCE_EDGE_CASES_MISSING")
        _must(truth["verified_ground_truth_cases"]==0,
              "FICTIONAL_INVOICES_PROMOTED_AS_INDEPENDENT_TRUTH")
        _must(truth["actual_cash_recovered_cents"]==0,
              "FICTITIOUS_PAYMENT_PROMOTED_AS_CASH")
        _must(truth["case_status_counts"].get("HOLD_BLIND_REVIEW_DISAGREEMENT")==1,
              "INDEPENDENT_REVIEW_DISAGREEMENT_SILENTLY_RESOLVED")
        altered=invented_fixture_book()
        altered["cases"][0]["documents"][0]["body"]+=" FORGED"
        _must(bool(validate_fixtures(altered,validation,as_of=today)),
              "INVOICE_DOCUMENT_TAMPER_ACCEPTED")
        from freight.research_pilot_preflight import (
            build_preflight, validate_preflight,
        )
        pilot=build_preflight(
            as_of=today, protocols=validation, sources=sources,
            rehearsal=rehearsal, ground=truth
        )
        _must(pilot["required_controls"]==18,
              "PILOT_DATA_AND_GOVERNANCE_REQUIREMENTS_INCOMPLETE")
        _must(pilot["unmet_requirements"]==18,
              "UNVERIFIED_PILOT_APPROVAL_SILENTLY_ACCEPTED")
        _must(pilot["real_invoices_received"]==0,
              "PILOT_SYNTHETIC_INVOICES_MISLABELED_AS_REAL")
        _must(pilot["fictional_test_case_reviewer_concordance"][
            "actual_independent_reviewer_reliability_established"] is False,
              "FICTIONAL_BLIND_VOTES_PROMOTED_TO_HUMAN_INDEPENDENCE")
        fraudulent=_read("research/PILOT_PREFLIGHT_20261011.json")
        fraudulent["gates"][0]["external_signoff_observed"]=True
        _must(bool(validate_preflight(
            fraudulent, validation, sources, rehearsal, truth, as_of=today)),
            "FORGED_CUSTOMER_PILOT_SIGNOFF_ACCEPTED")
        from freight.research_market_audit import (
            build_market_audit, validate_catalog as validate_cfs_audit,
        )
        cfs_market=build_market_audit(as_of=today,protocols=validation)
        _must(cfs_market["table_excerpt_rows"]==6,
              "CENSUS_PUBLIC_SOURCE_ROW_COVERAGE_INCOMPLETE")
        _must(cfs_market["published_estimate_measurements"][
            "truck_mode_value_components_equal_source_total"],
              "TRUCK_CLASSIFICATION_VALUE_SUM_WRONG")
        _must(cfs_market["published_estimate_measurements"][
            "truck_mode_weight_components_equal_source_total"],
              "TRUCK_CLASSIFICATION_TONNAGE_SUM_WRONG")
        _must(cfs_market["press_release_reconciliation"][
            "regional_flagged_conflicts"][0]["press_number_cleared_for_use"] is False,
              "PRESS_RELEASE_REGIONAL_CONTRADICTION_SILENTLY_CORRECTED")
        _must(cfs_market["market_ranking_or_recovery_tam_established"] is False,
              "SHIPMENT_VALUE_MISLABELLED_AS_FREIGHT_RECOVERY_MARKET")
        tampered_cfs=_read("research/CFS_2022_SOURCE_AUDIT_20261011.json")
        tampered_cfs["table_rows"][0]["value_million_usd"]*=1000
        _must(bool(validate_cfs_audit(tampered_cfs,validation,as_of=today)),
              "THOUSAND_MILLION_SOURCE_UNIT_TAMPER_ACCEPTED")
        from freight.research_cfs_archive_verifier import (
            build_readiness as build_cfs_byte_readiness,
            inspect_local_archive,
        )
        byte_status=build_cfs_byte_readiness(as_of=today)
        _must(byte_status["expected_row_count"]==6,
              "PRIMARY_CFS_ROW_TARGETS_MISSING")
        _must(byte_status["browser_observed_six_source_rows"]==6,
              "REMOTE_ORIGINAL_SOURCE_RECEIPT_INCOMPLETE")
        _must(byte_status["browser_observed_original_zip_sha256"]==
              "15d90f1e64c5b3fb86c5f619a32350f9c60256cc3eaaa48838115fc70f7d6499",
              "BROWSER_SOURCE_SHA256_DRIFT")
        _must(byte_status["original_archive_bytes_inspected_in_this_ci_run"] is False,
              "CI_UNFETCHED_CENSUS_SOURCE_BYTES_REPORTED_AS_READ")
        _must(byte_status["actual_official_zip_sha256_from_ci_run"] is None,
              "FAKE_CENSUS_CI_DIGEST_PROMOTED")
        _must(byte_status["south_press_discrepancy_officially_corrected"] is False,
              "UNSUPPORTED_CENSUS_EDITORIAL_CORRECTION")
        try:
            inspect_local_archive(b"not-a-census-zip", as_of=today)
        except ValueError:
            pass
        else:
            raise ValueError("UNVERIFIED_CENSUS_ARCHIVE_INPUT_ACCEPTED")
        from freight.research_cfs_industry_quality import (
            build_readiness as industry_readiness,
            validate_manifest as validate_industry_manifest,
        )
        industry=industry_readiness(as_of=today)
        _must(industry["public_archive_leads"]==2,
              "OFFICIAL_CFS_INDUSTRY_ARCHIVE_CENSUS_INCOMPLETE")
        _must(industry["remote_browser_original_rows_observed"]==14094,
              "CENSUS_INDUSTRY_SOURCE_ROWS_MISSING")
        _must(industry["remote_browser_flag_counts"]["CF2200A18"]["value"]["S"]==1839,
              "CFS_NON_PUBLISHABLE_GOODS_ESTIMATES_HIDDEN")
        _must(industry["remote_browser_flag_counts"]["CF2200A19"]["weight"]["S"]==1956,
              "CFS_NON_PUBLISHABLE_WEIGHT_ESTIMATES_HIDDEN")
        _must(industry["verified_paid_ltl_spend_usd"] is None and
              industry["buyer_demand_verified"] is False,
              "CFS_COMMODITY_SHIPMENT_VALUES_PROMOTED_TO_REAL_FREIGHT_INVOICES")
        _must(industry["source_rows_from_full_files_replayed_in_ci"]==0,
              "FAKE_FULL_CFS_FILE_REPLAY_FROM_CI")
        forged_industry=_read("research/CFS_A18_A19_INDUSTRY_RECEIPT_20261011.json")
        forged_industry["official_archives"][0]["value_flag_counts"]["S"]=0
        _must(bool(validate_industry_manifest(forged_industry,as_of=today)),
              "FABRICATED_CFS_INDUSTRY_QUALITY_COUNTS_ACCEPTED")
        from freight.research_industry_comparison import (
            build_comparison, validate_plan as validate_industry_comparison_plan,
        )
        compared=build_comparison(as_of=today,market_report=cfs_market)
        _must(compared["n_industries"]==3,
              "DIRECT_CENSUS_INDUSTRY_COMPARISON_MISSING")
        _must(compared["industry_comparisons"][0][
            "source_value_share_of_survey_covered_us_pct"]=="39.30",
              "INCORRECT_CENSUS_INDUSTRY_DENOMINATOR")
        _must(compared["market_or_customer_rankings_created"]==0 and
              compared["ltl_market_tam_usd"] is None,
              "UNVERIFIED_FREIGHT_RECOVERY_MARKET_PROMOTED")
        _must(all(row["within_industry_for_hire_shipment_value_share_pct"] is None
                  for row in compared["industry_comparisons"]),
              "MISSING_INDUSTRY_FORHIRE_SHARES_HALLUCINATED")
        falsified=_read("research/CFS_INDUSTRY_COMPARISON_PLAN_20261011.json")
        falsified["analysis_profiles"][2]["naics"]="493"
        _must(bool(validate_industry_comparison_plan(
            falsified,_read("research/CFS_A18_A19_INDUSTRY_RECEIPT_20261011.json"),
            as_of=today)),
            "UNVERIFIED_WAREHOUSE_NAICS_SUBSTITUTED")
        from freight.research_cfs_mode_hierarchy import build_forhire, validate_catalog as validate_mode_rows
        forhire=build_forhire(as_of=today,prior=compared)
        _must(forhire["qa"]["source_selected_rows"]==60,
              "CFS_FORHIRE_INDUSTRY_SOURCE_ROWS_MISSING")
        _must(forhire["three_sector_forhire_results"][0][
            "for_hire_goods_value_pct_of_this_sectors_all_mode_goods"]=="53.72",
              "INDUSTRY_FORHIRE_GOODS_SHARE_INCORRECT")
        _must(forhire["three_sector_forhire_results"][2][
            "combined_naics_484_and_captive_warehouse_population"] is True,
              "WAREHOUSE_SOURCE_MIXED_WITH_NAICS484_NOT_DISCLOSED")
        _must(forhire["qa"]["mirror_row_reproduction_against_original_census_dat_completed"] is False,
              "MIRRORED_RAW_DATA_MASQUERADING_AS_OFFICIAL_SHA_VALIDATION")
        _must(forhire["market_size_or_recovery_rates_established"] is False and
              forhire["actual_paid_ltl_invoices_observed"]==0,
              "CFS_SHIPPED_GOODS_MASQUERADING_AS_BILLING_RECOVERIES")
        forged_rows=_read("research/CFS_FORHIRE_NAICS_BUCKETS_20261011.json")
        forged_rows["selected_source_rows"][0]["mode_code"]="11"
        _must(bool(validate_mode_rows(forged_rows,as_of=today)),
              "INVALID_FORHIRE_OR_LTL_MODE_IDENTIFIER_ACCEPTED")
        from freight.research_ltl_revenue_bridge import (
            build_revenue, validate_catalog as validate_aies_source,
        )
        aies=build_revenue(as_of=today)
        _must(aies["ltl_2024_revenue_billion_usd"]=="65.096",
              "DIRECT_CENSUS_ORIGIN_LTL_CARRIER_REVENUE_NOT_RECONCILED")
        _must(aies["ltl_2024_share_of_all_trucking_pct"]=="16.16",
              "LTL_CARRIER_PARENT_INDUSTRY_DENOMINATOR_WRONG")
        _must(aies["ltl_freight_audit_recoverable_tam_usd"] is None and
              aies["real_ltl_invoice_cases_observed"]==0 and
              aies["commercial_uses_or_external_contact_allowed"] is False,
              "INDUSTRY_REVENUE_MISREPRESENTED_AS_AUDIT_RECOVERIES")
        _must(aies["source"]["full_census_origin_api_bytes_replayed"] is False,
              "UNREAD_OFFICIAL_AIES_API_MISREPRESENTED_AS_REPLAYED")
        false_aies=_read("research/AIES_LTL_CARRIER_REVENUE_20261011.json")
        false_aies["fred_aies_series"][-1]["observations"][-1][
            "revenue_thousand_usd"]=65_688_461
        _must(bool(validate_aies_source(false_aies,as_of=today)),
              "LEGACY_2022_REVENUE_SILENTLY_SUBSTITUTED_FOR_2024")
        from freight.research_aies_historical_lineage import (
            report_shell as build_historical,
            validate_manifest as validate_historical,
        )
        historical=build_historical(as_of=today)
        _must(historical["2023_national_ltl_thousand_usd"]==64651167,
              "CENSUS_2023_LTL_REVENUE_HISTORICAL_SOURCE_MISSING")
        _must(historical["2024_national_ltl_thousand_usd"]==65096292,
              "CENSUS_2024_LTL_REVENUE_SOURCE_MISSING")
        _must(historical["year_2022_status"].startswith("HOLD_") and
              historical["original_2023_and_2024_replayed_this_run"] is False,
              "LEGACY_SOURCE_OR_OFFLINE_CENSUS_MISREPRESENTED_AS_ORIGINAL_REPLAY")
        _must(historical["2023_to_2024_nominal_change_pct"]=="0.69" and
              historical["2022_to_2024_cagr_or_2022_to_2023_growth_promotion_allowed"] is False,
              "SURVEY_VINTAGE_DRIFT_MISTAKEN_FOR_AUDIT_FORECAST")
        _must(historical["recoverable_freight_audit_tam_usd"] is None and
              historical["actual_paid_ltl_invoices_observed"]==0 and
              historical["18_pilot_approval_requirements_unmet"] is True,
              "HISTORICAL_CARRIER_REVENUE_PROMOTED_TO_CUSTOMER_RECOVERIES")
        forged_historical=_read("research/AIES_HISTORICAL_LINEAGE_20261011.json")
        forged_historical["source_year_2022_original_reproduced"]=True
        _must(bool(validate_historical(forged_historical,as_of=today)),
              "UNREPLAYED_2022_CENSUS_PUBLISHER_DATA_SILENTLY_CERTIFIED")
        from freight.research_aies_2022_lineage import (
            _shell as build_m21_historic,
            validate_manifest as validate_m21_historic,
        )
        historical2022=build_m21_historic(today)
        _must(historical2022["status"]=="OFFLINE_HISTORICAL_METADATA_ONLY_NO_SOURCE_REPLAY",
              "M21_OFFLINE_DASHBOARD_CLAIMS_ORIGINAL_ZIP_REPLAY")
        _must(historical2022["published_2022_historical_ltl_revenue_thousand_usd"]==65688461,
              "M21_2022_CENSUS_HISTORICAL_REVENUE_MISSING")
        _must(historical2022["legacy_sas_gap_million_usd"]=="2722.539" and
              historical2022["legacy_sas_gap_assigned_causal_mechanism"] is None,
              "M21_2022_LEGACY_SAS_UNPROVEN_RECONCILIATION_CERTIFIED")
        _must(historical2022["2022_collected_under_standalone_original_aies_survey"] is False and
              historical2022["2022_cv_zero_means_exact_no_uncertainty"] is False,
              "M21_CENSUS_HISTORIC_LINKAGE_MISLABELED_DIRECT_SURVEY")
        _must(historical2022["actual_customer_invoice_rows_processed"]==0 and
              historical2022["ltl_recoverable_market_tam_usd"] is None and
              historical2022["human_pilot_18_controls_still_unverified"] is True,
              "M21_HISTORICAL_REVENUE_MISREPRESENTED_RECOVERY")
        forged_m21=_read("research/AIES_2022_LEGACY_LINEAGE_20261011.json")
        forged_m21["raw_2022_aies_standalone_survey_collected"]=True
        _must(bool(validate_m21_historic(forged_m21,as_of=today)),
              "M21_FAKE_STANDALONE_2022_AIES_ACCEPTED")
        from freight.research_sas_benchmark import (
            report_shell as build_sas_benchmark,
            validate_book as validate_sas_benchmark_book,
        )
        sas=build_sas_benchmark(as_of=today)
        _must(sas["status"]=="OFFLINE_SAS_SOURCE_VINTAGE_MANIFEST_ONLY_NOT_FRESH_ZIP_REPLAY",
              "SAS_BENCHMARK_OFFLINE_RESEARCH_FAKES_PUBLISHER_DOWNLOAD")
        _must(sas["vintage_2026_benchmarked_sas_million_usd"]==65688 and
              sas["vintage_2024_original_sas_million_usd"]==68411 and
              sas["revised_minus_old_sas_million_usd"]==-2723,
              "SAS_2022_BENCHMARK_REVISION_NOT_RECONCILED")
        _must(sas["aies_minus_revised_sas_million_usd"]=="0.461" and
              sas["aies_reconciles_to_published_benchmarked_sas_nearest_million"] is True,
              "SAS_AIES_HISTORICAL_2022_ROUNDING_COMPATIBILITY_MISSING")
        _must(sas["exact_modified_sas_sample_and_carryforward_factor_verified"] is False and
              sas["both_cvs_not_statistically_reconciled_or_independent_samples"] is True,
              "SAS_BENCHMARK_SPECIFIC_LATENT_ADJUSTMENT_FABRICATED")
        _must(sas["actual_customer_paid_invoices_observed"]==0 and
              sas["recoverable_freight_audit_tam_usd"] is None and
              sas["human_pilot_18_approval_requirements_unmet"] is True,
              "SAS_INDUSTRY_REVENUE_PROMOTED_TO_LTL_RECOVERY")
        forged_sas=_read("research/SAS_BENCHMARK_2022_EVIDENCE_20261011.json")
        forged_sas["revised_sas_cv_zero_means_exact_no_statistical_error"]=True
        _must(bool(validate_sas_benchmark_book(forged_sas,as_of=today)),
              "SAS_PUBLISHER_CV_ZERO_PROMOTED_TO_ERROR_FREE_CLAIM")
        from freight.research_sas_peer_benchmark import (
            report_shell as build_sas_peers,
            validate_manifest as validate_sas_peers,
        )
        peers=build_sas_peers(as_of=today)
        peer_rows={row["naics"]:row for row in peers["naics_peer_revisions"]}
        _must(peers["naics_industries_compared"]==3 and
              peers["all_three_industries_downward_revised"] is True and
              peers["ltl_revised_down_more_than_parent_or_tl_in_percentage_terms"] is False,
              "M23_SAS_BENCHMARK_NOT_GENERALIZED_ACROSS_TRUCKING_PEERS")
        _must([peer_rows[c]["signed_revision_million_usd"] for c in
              ("484","484121","484122")]==[-22238,-10765,-2723],
              "M23_SAS_PARENT_TRUCKLOAD_LTL_REVISIONS_DIFFER_FROM_SOURCE")
        _must(peers["ltl_original_parent_share_pct"]=="15.36" and
              peers["ltl_revised_parent_share_pct"]=="15.52" and
              peers["ltl_absolute_revision_share_of_parent_revision_pct"]=="12.24",
              "M23_PARENT_NAICS_OVERLAP_DENOMINATOR_INCORRECT")
        _must(peers["other_trucking_residual_revision_million_usd"]==-8750 and
              peers["other_trucking_residual_is_a_separate_surveyed_naics"] is False,
              "M23_CALCULATED_OTHER_TRUCKING_RESIDUAL_MISLABELLED_DIRECT_SURVEY")
        _must(peers["source_status"]=="OFFLINE_SAS_PEER_MANIFEST_NOT_ORIGINAL_REPLAY"
              and peers["original_workbooks_replayed_this_run"] is False,
              "M23_OFFLINE_SOURCE_UNLAWFULLY_PROMOTED_TO_VERIFIED")
        _must(peers["actual_independently_adjudicated_freight_invoices"]==0
              and peers["freight_recovery_tam_usd"] is None
              and peers["pilot_18_external_requirements_unmet"] is True,
              "M23_SURVEY_REVISIONS_MISTAKEN_FOR_CUSTOMER_RECOVERY_EVIDENCE")
        forged_peers=_read("research/SAS_TRUCKING_PEER_BENCHMARK_20261011.json")
        forged_peers["survey_revisions_are_carrier_billing_overcharges"]=True
        _must(bool(validate_sas_peers(forged_peers,as_of=today)),
              "M23_SOURCE_REVISIONS_FRAUDULENTLY_PROMOTED_TO_OVERCHARGES")
        from freight.research_sas_temporal import (
            report_shell as build_sas_temporal,
            validate_manifest as validate_sas_temporal,
        )
        temporal=build_sas_temporal(as_of=today)
        _must(temporal["2017_unchanged_anchor_categories"]==3 and
              temporal["2018_2022_downward_revised_categories_years"]==15,
              "M24_SAS_ORIGINAL_BENCHMARK_YEAR_REVISION_PATTERN_INCOMPLETE")
        _must(temporal["source_year_cells_changed"]==15 and
              temporal["unique_naics_year_vintage_comparisons"]==36,
              "M24_SAS_TEMPORAL_PEER_SOURCE_YEAR_GRAIN_MISSING")
        _must(temporal["source_status"]==
              "OFFLINE_PINNED_SOURCE_SNAPSHOT_ORIGINALS_NOT_REPLAYED_THIS_RUN" and
              temporal["census_original_workbooks_replayed_this_run"] is False,
              "M24_OFFLINE_SAS_RESEARCH_FAKES_NEW_PUBLISHER_SOURCE_REPLAY")
        _must(temporal["industry_comparisons"][2][
            "2017_to_2022_benchmarked_nominal_cumulative_growth_pct"]=="42.21" and
              temporal["industry_comparisons"][2][
            "2017_to_2022_older_vintage_nominal_cumulative_growth_pct"]=="48.10",
              "M24_LTL_VINTAGE_GROWTH_REVISED_2022_WRONG")
        _must(temporal["freight_invoice_error_rate_pct"] is None and
              temporal["actual_paid_customer_freight_invoice_sample_size"]==0 and
              temporal["recoverable_overpayment_market_usd"] is None and
              temporal["pilot_18_independent_external_controls_still_unmet"] is True,
              "M24_CENSUS_SURVEY_HISTORY_PROMOTED_TO_PAID_CUSTOMER_RECOVERIES")
        fake_temporal=_read("research/SAS_TEMPORAL_2017_2022_20261011.json")
        fake_temporal["published_2018_to_2022_revisions_can_be_called_invoice_errors"]=True
        _must(bool(validate_sas_temporal(fake_temporal,as_of=today)),
              "M24_FALSE_BILLING_ERROR_FROM_CENSUS_PUBLICATION_CHANGE_ACCEPTED")
        from freight.research_sas_aies_bridge import (
            report_shell as build_sas_aies_bridge,
            validate_catalog as validate_sas_aies_catalog,
        )
        bridge=build_sas_aies_bridge(as_of=today)
        _must(bridge["source_status"]==
              "OFFLINE_CENSUS_BRIDGE_PRIOR_VERIFIED_SNAPSHOTS_NO_NEW_SOURCE_REPLAY" and
              bridge["census_original_replay_completed_in_this_run"] is False,
              "M25_OFFLINE_CENSUS_BRIDGE_FALSE_NEW_ORIGINAL_REPLAY")
        _must(bridge["distinct_industry_year_values"]==24 and
              len(bridge["overlap_2022"])==3 and
              all(x["agrees_at_original_sas_nearest_million"]
                  for x in bridge["overlap_2022"]),
              "M25_SAS_AIES_2022_ROUNDING_CROSSWALK_INCOMPLETE")
        _must([x["2017_to_2024_nominal_cumulative_change_pct"]
               for x in bridge["industry_series"]]==["38.65","43.48","40.93"],
              "M25_TRUCKING_EIGHT_YEAR_SOURCE_VERSIONED_NOMINAL_REVENUE_WRONG")
        _must(bridge["industry_series"][2]["2023_to_2024_aies_nominal_change_pct"]
              =="0.69" and
              bridge["2022_aies_was_not_a_separately_fielded_2022_survey"] is True,
              "M25_2022_HISTORICAL_LEGACY_SAMPLE_FALSIFIED")
        _must(bridge["real_ltl_freight_invoice_cases_observed"]==0 and
              bridge["recoverable_freight_audit_market_usd"] is None and
              bridge["human_pilot_18_independent_requirements_unmet"] is True,
              "M25_EMPLOYER_REVENUE_MISREPRESENTED_AS_CUSTOMER_RECOVERIES")
        bad_bridge=_read("research/SAS_AIES_CARRIER_BRIDGE_2017_2024_20261012.json")
        bad_bridge["legacy_prebenchmark_2022_sas_can_substitute_for_revised_sas"]=True
        _must(bool(validate_sas_aies_catalog(bad_bridge,as_of=today)),
              "M25_OLD_SAS_VINTAGE_SILENTLY_PROMOTED_TO_LINKED_AIES_SOURCE")
        from freight.research_bls_ppi_bridge import (
            report_shell as build_bls_ppi,
            validate_catalog as validate_bls_ppi,
        )
        ppi=build_bls_ppi(as_of=today)
        ppi_codes={x["naics"]:x for x in ppi["industry_price_adjustments"]}
        _must(ppi["source_status"]==
              "OFFLINE_BLS_PPI_SNAPSHOT_NOT_REPLAYED_IN_THIS_RUN" and
              ppi["original_bls_public_api_replayed_this_run"] is False,
              "M26_OFFLINE_PPI_SNAPSHOT_PRETENDS_PUBLISHER_DOWNLOAD")
        _must(ppi["frozen_price_index_monthly_observations"]==192 and
              ppi["ppi_months_per_industry"]==96,
              "M26_BLS_MONTHLY_PPI_SOURCE_COVERAGE_MISSING")
        _must(ppi_codes["484121"][
            "2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"]
              =="2.82" and
              ppi_codes["484122"][
            "2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"]
              =="-1.89",
              "M26_INDUSTRY_PPI_ADJUSTMENT_CANNOT_REPRODUCE")
        _must(ppi["parent_trucking_naics484_price_adjusted_proxy_pct"] is None and
              ppi["parent_484_source_rejected_by_bls_v1_api_in_original_probe"] is True,
              "M26_MISSING_PARENT_PPI_FALSELY_INFERRED")
        _must(ppi["real_customer_freight_invoices_observed"]==0 and
              ppi["eligible_recovery_market_tam_usd"] is None and
              ppi["human_pilot_18_requirements_unmet"] is True,
              "M26_PRICE_INDEX_MISREPRESENTED_AS_CUSTOMER_RECOVERY_TAM")
        fake_ppi=_read("research/BLS_PPI_TRUCKING_2017_2024_20261012.json")
        fake_ppi["price_adjusted_revenue_proxy_is_official_real_output_measure"]=True
        _must(bool(validate_bls_ppi(fake_ppi,as_of=today)),
              "M26_ILLUSTRATIVE_PRICE_PROXY_PROMOTED_TO_OFFICIAL_REAL_OUTPUT")
        from freight.research_fred_parent_ppi import (
            report_shell as build_fred_parent,
            validate_catalog as validate_fred_parent,
        )
        fred=build_fred_parent(as_of=today)
        _must(fred["source_status"]==
              "FRED_PUBLIC_WEB_TABLE_SNAPSHOT_NOT_FRESH_CI_PUBLISHER_REPLAY"
              and fred["fresh_fred_distributor_http_replay_completed"] is False,
              "M27_FRED_WEB_SNAPSHOT_FRAUDULENTLY_CLAIMED_DIRECT_HTTP_REPLAY")
        _must(fred["source_months_2017_2024_in_web_observed_snapshot"]==96
              and fred["fresh_monthly_observations_verified_against_fred_http_this_run"]==0,
              "M27_FRED_PUBLIC_MONTH_COUNTS_WRONG_OR_FALSELY_AUTHENTICATED")
        _must(fred["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"]
              =="1.18" and
              fred["parent_2017_to_2024_fred_displayed_price_index_change_pct"]=="37.04",
              "M27_BLS_ORIGIN_FRED_TRUCKING_PRICE_PROXY_NOT_REPRODUCIBLE")
        _must(fred["source_is_direct_bls_api_verified"] is False and
              fred["m26_bls_original_api_parent_source_rejection_preserved"] is True and
              fred["parent_index_adjusted_estimate_can_be_marked_source_authenticated"] is False,
              "M27_FRED_SOURCE_PROVENANCE_PROMOTED_TO_BLS_DIRECT")
        _must(fred["client_paid_ltl_invoice_rows_observed"]==0 and
              fred["freight_recoverable_market_tam_usd"] is None and
              fred["human_customer_pilot_18_independent_requirements_still_unmet"] is True,
              "M27_PRODUCER_PRICE_INDEX_MISLABELED_CUSTOMER_AUDIT_REVENUE")
        fake_fred=_read("research/FRED_PARENT_484_PPI_2017_2024_20261012.json")
        fake_fred["direct_bls_authenticated_parent_index_available"]=True
        _must(bool(validate_fred_parent(fake_fred,as_of=today)),
              "M27_UNAUTHENTICATED_FRED_PARENT_SOURCE_ACCEPTED_AS_DIRECT_BLS")
        from freight.research_bls_parent_origin import (
            report_shell as build_native_parent_bls,
            validate_catalog as validate_native_parent_bls,
        )
        native=build_native_parent_bls(as_of=today)
        _must(native["source_status"]==
              "OFFLINE_PREVIOUS_NATIVE_BLS_V2_OBSERVATIONS_NOT_REPLAYED_IN_THIS_RUN"
              and native["original_bls_api_v2_months_replayed_this_execution"]==0,
              "M28_OFFLINE_DIRECT_BLS_SOURCE_FRAUDULENTLY_CLAIMED_LIVE")
        _must(native["native_bls_original_series_id"]=="PCU484---484---"
              and native["fred_redistributed_alias_series_id"]=="PCU484484"
              and native["bls_months_in_previous_first_party_probe"]==96,
              "M28_NATIVE_BLS_SERIES_ID_AND_96_MONTHS_NOT_RECONCILED")
        _must(native["2017_to_2024_census_nominal_revenue_change_pct"]=="38.65"
              and native["2017_to_2024_bls_parent_ppi_change_pct"]=="37.04"
              and native["2017_to_2024_illustrative_adjusted_revenue_proxy_pct"]=="1.18",
              "M28_FIRST_PARTY_BLS_PRICE_PROXY_NOT_REPRODUCIBLE")
        _must(native["historic_m27_fred_provisional_status_unchanged"] is True
              and native["index_adjustment_is_not_official_real_freight_output"] is True,
              "M28_FRED_HISTORY_OR_REAL_OUTPUT_SOURCE_MISREPRESENTED")
        _must(native["real_customer_freight_invoices_observed"]==0 and
              native["verified_recoverable_market_tam_usd"] is None and
              native["18_human_customer_pilot_requirements_unmet"] is True,
              "M28_BLS_PRICE_INDEX_MISTAKEN_FOR_PAID_FREIGHT_RECOVERIES")
        fake_native=_read("research/BLS_PARENT_ORIGIN_M28_20261012.json")
        fake_native["original_bls_series_id"]="PCU484484"
        _must(bool(validate_native_parent_bls(fake_native,as_of=today)),
              "M28_FRED_ALIAS_ACCIDENTALLY_AUTHORIZED_AS_BLS_NATIVE_ID")
        from freight.research_unified_blspci import (
            report_shell as build_unified_direct_bls,
            validate_policy as validate_unified_bls_policy,
        )
        direct=build_unified_direct_bls(as_of=today)
        ppi_compared={x["naics"]:x for x in direct["industry_comparisons"]}
        _must(direct["status"]==
              "M29_OFFLINE_PRIOR_BLS_SOURCE_OBSERVATIONS_NO_FRESH_THREE_SERIES_REPLAY"
              and direct["current_source_authenticated_month_count"]==0,
              "M29_OFFLINE_SOURCE_CONFLATED_WITH_FRESH_288_BLS_MONTHS")
        _must(direct["historical_original_bls_months_in_pinned_catalogs"]==288
              and direct["industry_counts"]==3
              and direct["source_series_ids"]==[
                  "PCU484---484---","PCU484121484121","PCU484122484122"],
              "M29_THREE_NATIVE_BLS_TRUCKING_SERIES_INCOMPLETE")
        _must([ppi_compared[x]["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]
               for x in ("484","484121","484122")]==["1.18","2.82","-1.89"],
              "M29_UNIFIED_SOURCE_PRICE_ADJUSTMENTS_CHANGED")
        _must(ppi_compared["484122"][
                  "2017_to_2024_december_endpoint_price_adjusted_revenue_pct"]=="1.60"
              and ppi_compared["484122"][
                  "2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]=="-1.89"
              and direct["december_endpoint_sensitivity_is_not_a_statistical_confidence_interval"],
              "M29_LTL_METHOD_SENSITIVITY_SUPPRESSED_OR_FALSLY_CERTIFIED")
        _must(direct["real_customer_freight_invoices_observed"]==0
              if "real_customer_freight_invoices_observed" in direct
              else direct["actual_paid_customer_freight_invoices_observed"]==0,
              "M29_SOURCE_MISTAKEN_FOR_CUSTOMER_INVOICE_SAMPLE")
        _must(direct["freight_recovery_market_tam_usd"] is None and
              direct["original_18_independent_pilot_requirements_still_unmet"],
              "M29_BLS_INDEX_PROMOTED_TO_VERIFIED_RECOVERY_MARKET")
        fake_unified=_read("research/BLS_TRUCKING_UNIFIED_SOURCE_POLICY_M29_20261012.json")
        fake_unified["december_endpoint_is_annual_average"]=True
        _must(bool(validate_unified_bls_policy(fake_unified,as_of=today)),
              "M29_FALSE_BLS_ANNUAL_AVERAGE_SUBSTITUTED_FROM_DECEMBER_MONTH")
        from freight.research_bea_measurement_gate import (
            report_shell as build_bea_measure_gate,
            validate_book as validate_bea_measure_book,
            measure_compatible as check_bea_measure_compatible,
        )
        bea_measure=build_bea_measure_gate(as_of=today)
        _must(bea_measure["status"]==
              "M30_OFFLINE_BEA_DEFINITIONS_PREVIOUSLY_VERIFIED_GROSS_OUTPUT_VALUES_HELD"
              and bea_measure["bea_original_measure_definitions_verified_in_this_run"] is False,
              "M30_OFFLINE_BEA_DEFINITIONS_MISLABELED_FRESH_SOURCE")
        _must(bea_measure["bea_gross_output_original_source_status"]==
              "HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED"
              and bea_measure["bea_484_real_gross_output_2017_2024_available_for_validation"] is False,
              "M30_UNRETRIEVED_BEA_GROSS_OUTPUT_FALSELY_PUBLISHED")
        _must(bea_measure["bea_value_added_2025_vintage_2017_to_2024_growth_pct"]=="1.41"
              and bea_measure["bea_value_added_2026_vintage_2017_to_2024_growth_pct"]=="-2.42"
              and bea_measure["bea_real_value_added_2024_index_revision_points"]=="-3.821",
              "M30_BEA_GDP_VALUE_ADDED_YEAR_VINTAGE_CLAIM_UNRELIABLE")
        _must(check_bea_measure_compatible(
                claimed="ILLUSTRATIVE_CENSUS_EMPLOYER_REVENUE_BLS_PPI_PROXY",
                benchmark="BEA_REAL_GDP_VALUE_ADDED_BY_INDUSTRY") is False
              and bea_measure["proxy_vs_bea_value_added_difference_is_model_error"] is False,
              "M30_BEA_VALUE_ADDED_MISUSED_AS_GROSS_OUTPUT_MODEL_VALIDATION")
        _must(bea_measure["real_invoice_rows_validated"]==0
              and bea_measure["recoverable_freight_market_tam_usd"] is None
              and bea_measure["all_18_real_customer_pilot_requirements_unmet"] is True,
              "M30_BEA_ECONOMIC_DATA_PROMOTED_TO_FREIGHT_RECOVERY")
        fake_bea=_read("research/BEA_TRUCKING_MEASURE_COMPATIBILITY_M30_20261012.json")
        fake_bea["original_gross_output_484_source_verified"]=True
        _must(bool(validate_bea_measure_book(fake_bea,as_of=today)),
              "M30_UNAUTHENTICATED_GROSS_OUTPUT_PROMOTED_TO_VERIFIED")
        from freight.research_bls_sectoral_output_m31 import (
            report_shell as build_bls_sectoral_output_m31,
            validate_catalog as validate_bls_sectoral_m31,
        )
        sectoral=build_bls_sectoral_output_m31(as_of=today)
        sectoral_by={row["naics"]:row for row in
                    sectoral["original_bls_sectoral_output_industry_series"]}
        _must(sectoral["status"]==
              "M31_OFFLINE_PRIOR_BLS_IP_SOURCE_OBSERVATION_NOT_FRESH_REPLAY" and
              sectoral["fresh_original_bls_source_year_cells_authenticated"]==0,
              "M31_OFFLINE_BLS_SECTORAL_REPORT_FALSELY_CREDITS_FRESH_SOURCE_REPLAY")
        _must(sectoral["historically_observed_original_bls_source_annual_cells"]==24
              and sectoral["original_bls_api_v2_native_ids"]==[
                  "IPUIN484___T010000000",
                  "IPUIN4841__T010000000",
                  "IPUIN48412_T010000000",
              ],
              "M31_BLS_INDUSTRY_PRODUCTIVITY_24_ANNUAL_SOURCE_CELLS_MISSING")
        _must([sectoral_by[c]["2017_2024_real_sectoral_output_change_pct"]
               for c in ("484","4841","48412")]==["4.02","5.91","2.98"],
              "M31_OFFICIAL_BLS_OUTPUT_INDUSTRIES_NOT_REPRODUCED")
        _must(sectoral["m29_aggregate_illustrative_census_ppi_revenue_proxy_2017_2024_pct"]
              =="1.18" and
              sectoral["bls_minus_ppi_proxy_descriptive_gap_percentage_points"]=="2.84" and
              sectoral["bls_real_sectoral_output_is_not_bea_gross_output"] is True and
              sectoral["gross_output_original_bea_naics484_source_still_unverified"] is True,
              "M31_BLS_OUTPUT_IMPROPERLY_USED_AS_BEAS_GROSS_OUTPUT_VALIDATION")
        _must(sectoral["real_paid_customer_freight_invoices_observed"]==0 and
              sectoral["recoverable_freight_audit_tam_usd"] is None and
              sectoral["original_18_real_customer_pilot_requirements_unmet"] is True,
              "M31_PUBLIC_SECTORAL_OUTPUT_MISTAKEN_FOR_PAID_CUSTOMER_RECOVERY")
        bad_sectoral=_read("research/BLS_SECTORAL_OUTPUT_M31_20261012.json")
        bad_sectoral["bls_original_sectoral_output_equals_official_bea_real_gross_output"]=True
        _must(bool(validate_bls_sectoral_m31(bad_sectoral,as_of=today)),
              "M31_ORIGINAL_BEAS_GROSS_OUTPUT_SOURCE_FABRICATED")
        return {"competitors":len(evidence["competitors"]),
                "source_status":"DATED_PUBLIC_SUMMARIES_NOT_INDEPENDENTLY_AUDITED",
                "research_lanes":len(brief["lanes"]),
                "source_records":brief["source_register_count"],
                "public_campaign_sources":13,
                "opposition_findings":brief["opposition_findings"],
                "research_receipt_sha256":brief["receipt_sha256"],
                "source_quote_anchors":proof["anchor_count"],
                "anchored_claims":proof["anchored_claim_count"],
                "evidence_receipt_sha256":proof["receipt_sha256"],
                "strategic_decisions":len(opposition["decisions"]),
                "opposition_receipt_sha256":opposition["receipt_sha256"],
                "refresh_queue_sources":queue["source_count"],
                "refresh_queue_receipt_sha256":queue["receipt_sha256"],
                "validation_design_count":validation["protocol_count"],
                "validation_design_receipt_sha256":validation["receipt_sha256"],
                "rehearsed_research_methods":rehearsal["rehearsed_protocols"],
                "invented_rehearsal_records":rehearsal["invented_case_records"],
                "synthetic_rehearsal_receipt_sha256":rehearsal["receipt_sha256"],
                "public_freight_source_leads":sources["source_leads"],
                "public_freight_source_readiness_sha256":sources["receipt_sha256"],
                "rights_cleared_freight_data_imports":sources["datasets_imported"],
                "ground_truth_instrument_cases":truth["case_count"],
                "ground_truth_instrument_receipt_sha256":truth["receipt_sha256"],
                "real_invoice_adjudications_completed":truth["verified_ground_truth_cases"],
                "pilot_unmet_human_evidence_requirements":pilot["unmet_requirements"],
                "pilot_preflight_receipt_sha256":pilot["receipt_sha256"],
                "approved_independent_customer_pilots":pilot["studies_with_pilot_data"],
                "cfs_published_table_excerpt_rows":cfs_market["table_excerpt_rows"],
                "cfs_unresolved_press_conflicts":len(cfs_market["press_release_reconciliation"]["regional_flagged_conflicts"]),
                "cfs_market_source_audit_receipt_sha256":cfs_market["receipt_sha256"],
                "cfs_original_archive_verification_status":byte_status["scope"],
                "cfs_original_archive_readiness_receipt_sha256":byte_status["receipt_sha256"],
                "cfs_original_archive_remote_browser_sha256":byte_status["browser_observed_original_zip_sha256"],
                "cfs_original_archive_bytes_replayed_in_ci":False,
                "cfs_industry_origins_observed":industry["public_archive_leads"],
                "cfs_industry_remote_source_rows":industry["remote_browser_original_rows_observed"],
                "cfs_industry_data_receipt_sha256":industry["receipt_sha256"],
                "cfs_three_sector_source_comparisons":compared["n_industries"],
                "cfs_industry_comparison_receipt_sha256":compared["receipt_sha256"],
                "cfs_forhire_industry_mode_111_source_rows":forhire["qa"]["source_selected_rows"],
                "cfs_forhire_source_receipt_sha256":forhire["receipt_sha256"],
                "cfs_forhire_source_remains_not_ltl_spend":True,
                "aies_ltl_2024_carrier_revenue_billion_usd":aies["ltl_2024_revenue_billion_usd"],
                "aies_ltl_2024_pct_of_all_trucking_revenue":aies["ltl_2024_share_of_all_trucking_pct"],
                "aies_ltl_revenue_receipt_sha256":aies["receipt_sha256"],
                "aies_ltl_revenue_is_not_recoverable_tam":True,
                "aies_historical_source_scope":historical["scope"],
                "aies_2023_research_revenue_thousand_usd":historical["2023_national_ltl_thousand_usd"],
                "aies_2023_to_2024_nominal_change_pct":historical["2023_to_2024_nominal_change_pct"],
                "aies_2022_primary_source_still_held":True,
                "aies_historical_source_receipt_sha256":historical["receipt_sha256"],
                "aies_2022_publisher_historic_snapshot":historical2022["scope"],
                "aies_2022_historic_ltl_thousand_usd":historical2022["published_2022_historical_ltl_revenue_thousand_usd"],
                "aies_2022_historic_original_zip_in_this_director_run":False,
                "aies_2022_legacy_sas_gap_causal_attribution_held":True,
                "aies_2022_historic_research_receipt_sha256":historical2022["receipt_sha256"],
                "sas_2022_old_source_million_usd":sas["vintage_2024_original_sas_million_usd"],
                "sas_2022_benchmarked_million_usd":sas["vintage_2026_benchmarked_sas_million_usd"],
                "sas_2022_pub_revision_million_usd":sas["revised_minus_old_sas_million_usd"],
                "sas_2022_rounding_reconciled_to_aies":sas["aies_reconciles_to_published_benchmarked_sas_nearest_million"],
                "sas_benchmark_original_xlsx_replayed_in_director":False,
                "sas_benchmark_source_receipt_sha256":sas["receipt_sha256"],
                "sas_peer_naics_2022_compared":peers["naics_industries_compared"],
                "sas_peer_all_trucking_revision_million_usd":peer_rows["484"]["signed_revision_million_usd"],
                "sas_peer_tl_revision_million_usd":peer_rows["484121"]["signed_revision_million_usd"],
                "sas_peer_ltl_revision_million_usd":peer_rows["484122"]["signed_revision_million_usd"],
                "sas_peer_ltl_relative_revision_not_unique":True,
                "sas_peer_source_receipt_sha256":peers["receipt_sha256"],
                "sas_temporal_revision_2017_anchor_categories":temporal["2017_unchanged_anchor_categories"],
                "sas_temporal_down_revised_2018_2022_source_cells":temporal["2018_2022_downward_revised_categories_years"],
                "sas_temporal_three_industry_periods":temporal["unique_naics_year_vintage_comparisons"],
                "sas_temporal_source_receipt_sha256":temporal["receipt_sha256"],
                "sas_aies_2017_2024_bridge_industry_year_cells":bridge["distinct_industry_year_values"],
                "sas_aies_2022_overlap_crosschecks":len(bridge["overlap_2022"]),
                "sas_aies_2017_2024_ltl_nominal_change_pct":bridge["industry_series"][2]["2017_to_2024_nominal_cumulative_change_pct"],
                "sas_aies_bridge_offline_not_new_original_replay":True,
                "sas_aies_bridge_evidence_receipt_sha256":bridge["receipt_sha256"],
                "bls_ppi_monthly_observation_snapshot_count":ppi["frozen_price_index_monthly_observations"],
                "bls_ppi_price_adjusted_ltl_proxy_pct":ppi_codes["484122"]["2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"],
                "bls_ppi_parent_trucking_price_adjustment_held":True,
                "bls_ppi_evidence_receipt_sha256":ppi["receipt_sha256"],
                "fred_parent_484_provisional_ppi_proxy_pct":fred["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"],
                "fred_parent_484_source_web_months":fred["source_months_2017_2024_in_web_observed_snapshot"],
                "fred_parent_484_direct_bls_authentication_complete":False,
                "fred_parent_484_direct_fred_http_replayed_in_director":False,
                "fred_parent_484_evidence_receipt_sha256":fred["receipt_sha256"],
                "bls_native_parent_484_source_id":native["native_bls_original_series_id"],
                "bls_native_parent_484_full_history_previous_probe_months":native["bls_months_in_previous_first_party_probe"],
                "bls_native_parent_484_offline_not_fresh_api_replay":True,
                "bls_native_parent_484_price_proxy_pct":native["2017_to_2024_illustrative_adjusted_revenue_proxy_pct"],
                "bls_native_parent_484_source_receipt_sha256":native["receipt_sha256"],
                "bls_three_industry_native_ids":direct["source_series_ids"],
                "bls_three_industry_months_in_original_source_snapshots":direct["historical_original_bls_months_in_pinned_catalogs"],
                "bls_three_industry_current_research_offline_not_fresh_source":True,
                "bls_ltl_2017_2024_annual_mean_proxy_pct":ppi_compared["484122"]["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"],
                "bls_ltl_2017_2024_december_sensitivity_pct":ppi_compared["484122"]["2017_to_2024_december_endpoint_price_adjusted_revenue_pct"],
                "bls_three_industry_unified_receipt_sha256":direct["receipt_sha256"],
                "bea_2025_old_value_added_2024_index":bea_measure["bea_value_added_2025_vintage_2024_index_2017eq100"],
                "bea_2026_revised_value_added_2024_index":bea_measure["bea_value_added_2026_vintage_2024_index_2017eq100"],
                "bea_current_gross_output_484_not_yet_source_authenticated":True,
                "bea_value_added_not_sufficient_to_certify_bls_ppi_output_proxy":True,
                "bea_measure_compatibility_source_receipt_sha256":bea_measure["receipt_sha256"],
                "bls_real_sectoral_original_source_ids":sectoral["original_bls_api_v2_native_ids"],
                "bls_real_sectoral_484_2017_2024_change_pct":sectoral["aggregate_naics484_real_sectoral_output_2017_2024_pct"],
                "bls_real_sectoral_vs_ppi_proxy_descriptive_gap_pp":sectoral["bls_minus_ppi_proxy_descriptive_gap_percentage_points"],
                "bls_real_sectoral_not_bea_gross_output":True,
                "bls_real_sectoral_source_receipt_sha256":sectoral["receipt_sha256"],
                "sas_temporal_source_does_not_establish_freight_recovery":True,
                "cfs_sector_real_ltl_spend_known":False,
                "cfs_industry_paid_invoice_market_proven":False,
                "ltl_recovery_market_established":False,
                "independent_customer_studies_completed":0,
                "source_refresh_automated":False},"STALE_AND_TAMPERED_SOURCE_ASSERTIONS_REJECTED"
    raise ValueError("UNSUPPORTED_LAB")


def execute_all_labs(*, record,authority_book,store,assertions,fee_events,verifier,
                     contingency: ContingencyAssumptions, max_labs: int=14) -> dict:
    if type(max_labs) is not int or not 1<=max_labs<=14:
        raise ValueError("INVALID_EXECUTION_BUDGET")
    initial=execute_domain_chain(record=record,authority_book=authority_book,
                                 store=store,assertions=assertions,fee_events=fee_events,
                                 verifier=verifier,contingency=contingency)
    executed={}
    for row in initial["lab_executions"]:
        if row["lab"] in BASE_FIVE:
            executed[row["lab"]]={"lab":row["lab"],"title":LAB_LABELS[row["lab"]],
                  "status":"EXECUTED_EXISTING_PYTHON_DOMAIN",
                  "proof":{"phase3_step":row["status"],"evidence":row.get("evidence")},
                  "negative_probe":"INHERITED_PHASE3_VALIDATED_CASES",
                  "scope":"ISOLATED_SYNTHETIC","elapsed_ms":row.get("elapsed_ms")}
    for lab in sorted(EXTENSIONS):
        if len(executed)>=max_labs:break
        start=perf_counter_ns()
        try:
            proof,negative=_run_extension(lab,record=record,authority_book=authority_book,assumptions=contingency)
            row={"lab":lab,"title":LAB_LABELS[lab],"status":"EXECUTED_EXISTING_PYTHON_MODULE",
                 "proof":proof,"negative_probe":negative,"scope":"SYNTHETIC_OR_SOURCE_INSPECTED",
                 "elapsed_ms":(perf_counter_ns()-start)//1_000_000}
        except Exception as exc:
            row={"lab":lab,"title":LAB_LABELS[lab],"status":"FAILED_OR_BLOCKED",
                 "reason":type(exc).__name__+":"+str(exc)[:180],
                 "negative_probe":"NOT_VERIFIED","scope":"SYNTHETIC_OR_SOURCE_INSPECTED",
                 "elapsed_ms":(perf_counter_ns()-start)//1_000_000}
        executed[lab]=row
    for lab in LAB_LABELS:
        if lab not in executed:
            executed[lab]={"lab":lab,"title":LAB_LABELS[lab],"status":"NOT_EXECUTED_BUDGET",
                           "scope":"NOT_EXECUTED","negative_probe":"NOT_RUN","elapsed_ms":None}
    rows=[executed[i] for i in sorted(executed)]
    stable=[{k:v for k,v in x.items() if k!="elapsed_ms"} for x in rows]
    base={"schema":1,"scope":"BOUNDED_ISOLATED_RESEARCH_ONLY",
          "production_api_executed":False,"actual_revenue_cents":0,
          "hosted_staging_certified":False,"customer_bank_carrier_authority_proven":False,
          "source_first_party": "ACTUAL_REPOSITORY_PYTHON_MODULES_WITH_FICTIONAL_FIXTURES",
          "lab_runs":rows,
          "executed_labs":[x["lab"] for x in rows if x["status"].startswith("EXECUTED")],
          "failed_or_blocked_labs":[x["lab"] for x in rows if not x["status"].startswith("EXECUTED")],
          "three_customer_pilot":simulated_cohort(),
          "historical_findings_open":26,
          "laboratory_executions_not_equivalent_to_customer_accuracy":True,
          "prior_chain_receipt":initial["receipt_sha256"]}
    hashed={**base,"lab_runs":stable}
    base["receipt_sha256"]=digest(hashed)
    return base


def priority_actions(receipt: dict) -> list[dict]:
    actions=[]
    if receipt["failed_or_blocked_labs"]:
        actions.append({"priority":1,"action":"Repair failed laboratory execution",
                        "labs":receipt["failed_or_blocked_labs"],
                        "basis":"EXACT_HEAD_RESEARCH_FAILED"})
    actions.extend([
        {"priority":2,"action":"Provision segregated Floot staging database/project, mock external providers",
         "basis":"BLOCKED_HOSTED_ISOLATION_UNVERIFIED"},
        {"priority":3,"action":"Establish independent buyer/carrier/bank evidence authority",
         "basis":"EXTERNAL_CONTROL_NOT_AVAILABLE"},
        {"priority":4,"action":"Exercise concurrent provider retries inside isolated staging",
         "basis":"SOURCE_LEVEL_REPLAY_TESTS_ONLY"},
        {"priority":5,"action":"Calibrate contingency probabilities from permissioned real outcomes",
         "basis":"ALL_CURRENT_PROBABILITIES_MODELED"},
    ])
    return actions
