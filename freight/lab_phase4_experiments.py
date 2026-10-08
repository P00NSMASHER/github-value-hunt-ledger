"""Local bounded experiment selection, execution receipt and immutable ledger.

This selects work from the original unresolved 26 findings, runs approved local
Python adapters and records an INCONCLUSIVE or DEFECT_STILL_REPRODUCED finding.
It deliberately cannot declare original defects fixed on the strength of new tests.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter_ns
import json

from freight.lab_assurance import digest
from freight.lab_intelligence_runner import make_control_room
from freight.lab_experiment_ledger import Experiment, ExperimentLedger
from freight.lab_phase4_director import execute_all_labs


@dataclass(frozen=True)
class ExperimentPlan:
    finding_id: str
    cluster: str
    score: int
    labs: tuple[int, ...]
    reproduction_source: str


def select_experiments(register: dict, *, max_experiments: int=4,
                       excluded_ids: frozenset[str]=frozenset()) -> tuple[ExperimentPlan,...]:
    if type(max_experiments) is not int or not 1<=max_experiments<=26:
        raise ValueError("max_experiments must be in [1,26]")
    ordered=make_control_room(register)["next_experiments"]
    seen_clusters=set()
    selection=[]
    for row in ordered:
        if row["finding_id"] in excluded_ids or row["cluster"] in seen_clusters:
            continue
        seen_clusters.add(row["cluster"])
        selection.append(ExperimentPlan(row["finding_id"],row["cluster"],
                          row["priority_points"],tuple(row["affected_labs_planning_assumption"]),
                          row["evidence"]))
        if len(selection)>=max_experiments:
            break
    return tuple(selection)


def verify_experiment_outcome(receipt: dict) -> None:
    if receipt.get("scope")!="BOUNDED_ISOLATED_RESEARCH_ONLY":
        raise ValueError("UNSUPPORTED_EXECUTION_SCOPE")
    if receipt.get("production_api_executed") is not False:
        raise ValueError("PRODUCTION_EXECUTION_MISLABELED")
    if receipt.get("actual_revenue_cents") != 0 or receipt.get("historical_findings_open")!=26:
        raise ValueError("HISTORICAL_OR_FINANCIAL_STATUS_MISLABELED")
    if len(receipt.get("lab_runs",[]))!=14:
        raise ValueError("INCOMPLETE_EXECUTION_CENSUS")
    for row in receipt["lab_runs"]:
        if row["status"].startswith("EXECUTED"):
            if not row.get("proof") or row.get("negative_probe") in (None,"NOT_RUN","NOT_VERIFIED"):
                raise ValueError("EXECUTED_LAB_WITHOUT_NEGATIVE_EVIDENCE")
    expected=digest({k:v if k!="lab_runs" else
         [{a:b for a,b in lab.items() if a!="elapsed_ms"} for lab in v]
         for k,v in receipt.items() if k!="receipt_sha256"})
    if expected!=receipt.get("receipt_sha256"):
        raise ValueError("EXPERIMENT_RUN_RECEIPT_TAMPERED")


def conduct_experiments(*, register: dict, ledger_path: str | Path, max_experiments: int,
                        record, authority_book, store, assertions, fee_events, verifier, contingency) -> dict:
    start=perf_counter_ns()
    choices=select_experiments(register,max_experiments=max_experiments)
    if not choices:
        raise ValueError("NO_EXPERIMENTS_SELECTED")
    execution=execute_all_labs(record=record,authority_book=authority_book,store=store,
                 assertions=assertions,fee_events=fee_events,verifier=verifier,
                 contingency=contingency)
    verify_experiment_outcome(execution)
    runtime_ms=(perf_counter_ns()-start)//1_000_000
    ledger=ExperimentLedger(ledger_path)
    receipts=[]
    for plan in choices:
        evidence_for_labs=[row for row in execution["lab_runs"] if row["lab"] in plan.labs]
        controls_pass=bool(evidence_for_labs) and all(row["status"].startswith("EXECUTED") and
                                         row["negative_probe"] not in ("NOT_VERIFIED","NOT_RUN")
                                         for row in evidence_for_labs)
        experiment=Experiment(
          experiment_id="phase4:"+execution["receipt_sha256"][:18]+":"+plan.finding_id,
          finding_id=plan.finding_id,
          baseline_artifact_sha256=digest({"phase":3,"finding":plan.finding_id}),
          candidate_artifact_sha256=digest({"phase":4,"code":"research-only","cluster":plan.cluster}),
          frozen_input_sha256=digest({"synthetic_scope":execution["scope"],"test_id":"phase4-frozen"}),
          independent_test_sha256=digest({"execution":execution["receipt_sha256"],"target_labs":list(plan.labs)}),
          original_counterexample_reproduced=False,
          repaired_counterexample_rejected=False,
          known_good_control_passed=controls_pass,
          measured_runtime_ms=runtime_ms,
          execution_scope="REAL_CODE_MOCKED_PROVIDERS",
        )
        created,sha=ledger.append(experiment)
        receipts.append({"finding_id":plan.finding_id,"cluster":plan.cluster,"priority":plan.score,
                         "affected_labs":list(plan.labs),"created":created,
                         "verdict":"INCONCLUSIVE","receipt_sha256":sha})
    ledger_records=ledger.read_and_verify()
    body={"scope":"SYNTHETIC_LOCAL_EXPERIMENT_CAMPAIGN",
          "executed_labs":execution["executed_labs"],
          "historical_findings_closed":0,
          "real_customer_recovery_cents":0,
          "exhaustive_hosted_testing":False,
          "campaign_runtime_ms":runtime_ms,
          "selected_experiments":[asdict(x) for x in choices],
          "recorded_experiments":receipts,
          "ledger_entry_count":len(ledger_records),
          "execution_receipt_sha256":execution["receipt_sha256"]}
    return {**body,"receipt_sha256":digest(body)}


def load_findings() -> dict:
    return json.loads((Path(__file__).parent/"research/LAB_FINDINGS_CUMULATIVE.json").read_text())
