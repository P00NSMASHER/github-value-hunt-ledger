#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_learning_policy.json").read_text(encoding="utf-8"))
metrics=json.loads((INTEL/"routing_learning_metrics.json").read_text(encoding="utf-8"))
runs=load_jsonl("routing_learning_runs.jsonl")
adjustments=load_jsonl("routing_adjustments.jsonl")
claims=load_jsonl("execution_claim_history.jsonl")
search_runs=load_jsonl("search_runs.jsonl")

claim_by_run={c.get("search_run_id"):c for c in claims if c.get("search_run_id")}
search_by_id={r.get("search_run_id"):r for r in search_runs if r.get("search_run_id")}
gen=metrics.get("routing_learning_generation_id")
if not gen or not gen.startswith("ROUTELEARN:"):
    raise SystemExit("routing_learning_metrics missing generation id")
for n,r in enumerate(runs,1):
    if r.get("routing_learning_generation_id")!=gen:
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: generation drift")
    if not (0<=float(r.get("utility"))<=1):
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: utility out of range")
    src=search_by_id.get(r.get("search_run_id"))
    c=claim_by_run.get(r.get("search_run_id"))
    if not src or int(src.get("schema_version") or 0)<12:
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: source run missing/pre-v12")
    if src.get("routing_mode")!="generated":
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: non-generated route leaked into learner")
    if src.get("measurement_quality") not in set(POL.get("eligible_measurement_quality") or []):
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: ineligible measurement quality")
    if not c or c.get("status")!="COMPLETE" or c.get("telemetry_status")!="MATCHED":
        raise SystemExit(f"routing_learning_runs.jsonl:{n}: claim not complete/matched")

min_global=int(POL.get("min_global_generated_completions",12))
max_pos=float(POL.get("max_positive_adjustment",3.0))
max_neg=float(POL.get("max_negative_adjustment",2.0))
eligible_count=0
for n,a in enumerate(adjustments,1):
    if a.get("routing_learning_generation_id")!=gen:
        raise SystemExit(f"routing_adjustments.jsonl:{n}: generation drift")
    adj=float(a.get("adjustment") or 0)
    if adj>max_pos+1e-9 or adj<-max_neg-1e-9:
        raise SystemExit(f"routing_adjustments.jsonl:{n}: adjustment exceeds configured bounds")
    if a.get("eligible_for_routing"):
        eligible_count+=1
        if metrics.get("generated_completed_routes",0)<min_global:
            raise SystemExit("eligible adjustment before global evidence threshold")
        if int(a.get("worker_runs") or 0)<int(POL.get("min_worker_context_runs",3)):
            raise SystemExit(f"routing_adjustments.jsonl:{n}: insufficient worker runs")
        if int(a.get("baseline_runs") or 0)<int(POL.get("min_context_baseline_runs",5)):
            raise SystemExit(f"routing_adjustments.jsonl:{n}: insufficient baseline runs")
        if int(a.get("baseline_distinct_workers") or 0)<int(POL.get("min_context_distinct_workers",2)):
            raise SystemExit(f"routing_adjustments.jsonl:{n}: insufficient distinct workers")
        deep=int(a.get("worker_deep_inspected") or 0)
        outs=int(a.get("worker_valid_outcome_runs") or 0)
        if deep<int(POL.get("min_worker_context_deep_inspections",8)) and outs<int(POL.get("min_worker_context_outcome_runs",2)):
            raise SystemExit(f"routing_adjustments.jsonl:{n}: insufficient activity evidence")
        if abs(float(a.get("residual") or 0))<float(POL.get("min_abs_residual",0.10))-1e-9:
            raise SystemExit(f"routing_adjustments.jsonl:{n}: residual below threshold")
if eligible_count!=int(metrics.get("eligible_adjustments") or 0):
    raise SystemExit("routing_learning_metrics eligible_adjustments drift")
if metrics.get("generated_completed_routes",0)<min_global and eligible_count:
    raise SystemExit("observe-only threshold violated")
print(f"OK generated_routes={metrics.get('generated_completed_routes')} adjustments={len(adjustments)} eligible={eligible_count} mode={metrics.get('mode')}")
