#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"activation_response_policy.json").read_text(encoding="utf-8"))
REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
ACT=load_jsonl("activation_history.jsonl")
RUNS=load_jsonl("activation_response_runs.jsonl")
METRICS=load_jsonl("worker_activation_response_metrics.jsonl")
ADJ=load_jsonl("activation_response_adjustments.jsonl")
SUMMARY=json.loads((INTEL/"activation_response_metrics.json").read_text(encoding="utf-8"))

workers={x["worker_id"] for x in REG.get("workers",[])}
if len(RUNS)!=len(ACT):
    raise SystemExit("activation response must contain exactly one record per activation history entry")
if len({x.get("activation_id") for x in RUNS})!=len(RUNS):
    raise SystemExit("duplicate activation response record")
if {x["worker_id"] for x in METRICS}!=workers or len(METRICS)!=len(workers):
    raise SystemExit("worker activation-response metrics must contain every registered worker exactly once")
if {x["worker_id"] for x in ADJ}!=workers or len(ADJ)!=len(workers):
    raise SystemExit("activation-response adjustments must contain every registered worker exactly once")

gens={x.get("response_learning_generation_id") for x in RUNS+METRICS+ADJ}
if len(gens)>1:
    raise SystemExit("response learning generation drift")
if gens and SUMMARY.get("response_learning_generation_id")!=next(iter(gens)):
    raise SystemExit("response learning summary generation mismatch")

global_threshold=int(POL.get("global_min_resolved_primary_activations",20))
max_pen=float(POL.get("max_negative_routing_adjustment",1.0))
global_sufficient=SUMMARY.get("global_resolved_primary_activations",0)>=global_threshold

for n,r in enumerate(RUNS,1):
    if r.get("ready_to_activation_minutes") is not None and r["ready_to_activation_minutes"]<0:
        raise SystemExit(f"activation_response_runs.jsonl:{n}: negative ready->activation latency")
    if r.get("activation_to_claim_minutes") is not None and r["activation_to_claim_minutes"]<0:
        raise SystemExit(f"activation_response_runs.jsonl:{n}: negative activation->claim latency")
    if r.get("lifecycle_state")=="PENDING" and r.get("claimed"):
        raise SystemExit(f"activation_response_runs.jsonl:{n}: pending activation marked claimed")

metrics_by={x["worker_id"]:x for x in METRICS}
for n,a in enumerate(ADJ,1):
    val=float(a.get("routing_response_adjustment") or 0)
    if val>1e-12:
        raise SystemExit(f"activation_response_adjustments.jsonl:{n}: positive adjustment is forbidden")
    if val < -max_pen-1e-12:
        raise SystemExit(f"activation_response_adjustments.jsonl:{n}: adjustment exceeds negative bound")
    m=metrics_by[a["worker_id"]]
    eligible=bool(a.get("eligible_for_routing"))
    if eligible!=bool(m.get("sufficient_response_evidence")):
        raise SystemExit(f"activation_response_adjustments.jsonl:{n}: eligibility drift")
    if eligible and not global_sufficient:
        raise SystemExit(f"activation_response_adjustments.jsonl:{n}: eligible before global threshold")
    if not eligible and abs(val)>1e-12:
        raise SystemExit(f"activation_response_adjustments.jsonl:{n}: insufficient evidence must have zero adjustment")

resolved=sum(1 for x in RUNS if x.get("dispatch_kind")=="primary" and x.get("lifecycle_state") in {"EXPIRED_UNCLAIMED","CLAIMED","COMPLETED","CLAIM_ENDED_OTHER"})
if resolved!=SUMMARY.get("global_resolved_primary_activations"):
    raise SystemExit("response summary resolved-primary count drift")
expected_mode="measured_feedback" if global_sufficient else "observe_only_insufficient_evidence"
if SUMMARY.get("mode")!=expected_mode:
    raise SystemExit("response learning mode drift")
print(f"OK mode={expected_mode} activations={len(RUNS)} resolved_primary={resolved} workers={len(workers)}")
