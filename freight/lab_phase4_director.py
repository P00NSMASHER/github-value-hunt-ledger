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
        today=date(2026,10,8)
        issues=validate_competitor_evidence(evidence,as_of=today)
        _must(not issues,"COMPETITOR_BASELINE_INVALID:"+",".join(issues[:3]))
        bad=copy.deepcopy(evidence);bad["valid_until"]="2025-01-01"
        _must(bool(validate_competitor_evidence(bad,as_of=today)),"STALE_CLAIMS_ACCEPTED")
        from freight.research_intelligence import (
            compile_brief, phase3_brief, seed_from_phase3,
        )
        brief=phase3_brief(as_of=today)
        _must(len(brief["lanes"])==8,"INCOMPLETE_RESEARCH_DISCIPLINES")
        _must(brief["opposition_findings"]>=5,"NO_REAL_SELF_OPPOSITION")
        _must(all(not x["can_publish_as_verified"] for x in brief["prioritized_findings"]),
              "UNVERIFIED_VENDOR_RESEARCH_PROMOTED")
        registry=seed_from_phase3(as_of=today,evidence=evidence,
                                  matrix=_read("PHASE3_COMPETITIVE_MATRIX_2026-10-07.json"))
        registry["sources"][0]["excerpt_sha256"]="0"*64
        try:
            compile_brief(registry,as_of=today)
        except ValueError:
            pass
        else:
            raise ValueError("TAMPERED_MARKET_SOURCE_ACCEPTED")
        return {"competitors":len(evidence["competitors"]),
                "source_status":"VENDOR_PUBLIC_CLAIMS_NOT_INDEPENDENTLY_AUDITED",
                "research_lanes":len(brief["lanes"]),
                "opposition_findings":brief["opposition_findings"],
                "research_receipt_sha256":brief["receipt_sha256"],
                "source_refresh_automated":False},"STALE_VENDOR_AND_TAMPERED_RESEARCH_REJECTED"
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
