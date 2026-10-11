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
