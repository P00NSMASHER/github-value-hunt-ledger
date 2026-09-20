#!/usr/bin/env python3
import hashlib, json, math
from collections import defaultdict
from statistics import mean
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_learning_policy.json").read_text(encoding="utf-8"))
RUNS=load_jsonl("search_runs.jsonl")
CLAIMS=load_jsonl("execution_claim_history.jsonl") if (INTEL/"execution_claim_history.jsonl").exists() else []
OUTCOMES=load_jsonl("outcomes.jsonl") if (INTEL/"outcomes.jsonl").exists() else []

allowed_quality=set(POL.get("eligible_measurement_quality") or [])
allowed_modes=set(POL.get("eligible_routing_modes") or [])
claims_by_run={
  c.get("search_run_id"):c for c in CLAIMS
  if c.get("status")=="COMPLETE" and c.get("telemetry_status")=="MATCHED" and c.get("search_run_id")
}
outcomes_by_run=defaultdict(list)
for o in OUTCOMES:
    if o.get("result")=="INVALID":
        continue
    for rid in o.get("origin_search_ids") or []:
        outcomes_by_run[rid].append(o)

def run_utility(r,outs):
    weighted=[]
    deep=int(r.get("deep_inspected") or 0)
    retained=int(r.get("retained_count") or 0)
    if deep>0:
        weighted.append((max(0.0,min(1.0,retained/deep)),0.20,"retained_precision"))
    cap_delta=1.0 if (r.get("new_capability_ids") or []) else (0.6 if (r.get("strengthened_capability_ids") or []) else 0.0)
    weighted.append((cap_delta,0.25,"capability_delta"))
    weighted.append((1.0 if int(r.get("master_promoted_count") or 0)>0 else 0.0,0.15,"master_promotion"))
    dispositions=r.get("candidate_dispositions") or []
    if dispositions:
        dup=sum(1 for d in dispositions if d.get("duplicate_of") or d.get("reason_code_standard")=="duplicate_or_dominated")
        weighted.append((1.0-(dup/len(dispositions)),0.10,"duplicate_free"))
    if outs:
        weighted.append((1.0,0.15,"valid_outcome"))
        weighted.append((1.0 if any(o.get("result")=="PASSED" for o in outs) else 0.0,0.15,"passed_outcome"))
    denom=sum(w for _,w,_ in weighted) or 1.0
    utility=sum(v*w for v,w,_ in weighted)/denom
    return round(max(0.0,min(1.0,utility)),6),{name:round(v,6) for v,_,name in weighted}

def contexts(r):
    out=[]
    vals=[
      ("role",r.get("assignment_slot_role")),
      ("work_kind",r.get("assignment_work_kind")),
      ("strategy",r.get("strategy_id")),
      ("objective",r.get("search_objective_id"))
    ]
    for dim,key in vals:
        if key: out.append((dim,key))
    for e in sorted(set(r.get("experiment_ids") or [])):
        out.append(("experiment",e))
    return out

learning_runs=[]
excluded={"manual_override":0,"unrouted":0,"retrospective":0,"unmatched_claim":0,"pre_v12":0}
for r in RUNS:
    version=int(r.get("schema_version") or 0)
    if version<12:
        excluded["pre_v12"]+=1
        continue
    if r.get("measurement_quality") not in allowed_quality:
        excluded["retrospective"]+=1
        continue
    mode=r.get("routing_mode")
    if mode not in allowed_modes:
        if mode=="manual_override": excluded["manual_override"]+=1
        else: excluded["unrouted"]+=1
        continue
    c=claims_by_run.get(r.get("search_run_id"))
    if not c:
        excluded["unmatched_claim"]+=1
        continue
    outs=outcomes_by_run.get(r.get("search_run_id"),[])
    utility,parts=run_utility(r,outs)
    learning_runs.append({
      "search_run_id":r.get("search_run_id"),
      "claim_id":c.get("claim_id"),
      "worker_id":r.get("execution_worker_id"),
      "routing_generation_id":r.get("routing_generation_id"),
      "worker_profile_generation_id":r.get("worker_profile_generation_id"),
      "routing_score":r.get("routing_score"),
      "slot_role":r.get("assignment_slot_role"),
      "work_kind":r.get("assignment_work_kind"),
      "strategy_id":r.get("strategy_id"),
      "search_objective_id":r.get("search_objective_id"),
      "experiment_ids":r.get("experiment_ids") or [],
      "deep_inspected":int(r.get("deep_inspected") or 0),
      "retained_count":int(r.get("retained_count") or 0),
      "valid_outcome":bool(outs),
      "passed_outcome":any(o.get("result")=="PASSED" for o in outs),
      "utility":utility,
      "utility_components":parts,
      "contexts":[{"dimension":d,"context_key":k} for d,k in contexts(r)]
    })

global_n=len(learning_runs)
group=defaultdict(list)
for rr in learning_runs:
    for c in rr["contexts"]:
        group[(c["dimension"],c["context_key"])].append(rr)

adjustments=[]
prior=float(POL.get("shrinkage_prior_runs",5))
scale=float(POL.get("adjustment_scale_points_per_utility",10))
min_global=int(POL.get("min_global_generated_completions",12))
min_worker_runs=int(POL.get("min_worker_context_runs",3))
min_worker_deep=int(POL.get("min_worker_context_deep_inspections",8))
min_worker_out=int(POL.get("min_worker_context_outcome_runs",2))
min_base=int(POL.get("min_context_baseline_runs",5))
min_workers=int(POL.get("min_context_distinct_workers",2))
min_resid=float(POL.get("min_abs_residual",0.10))
max_pos=float(POL.get("max_positive_adjustment",3.0))
max_neg=float(POL.get("max_negative_adjustment",2.0))

for (dim,key),rs in sorted(group.items()):
    baseline_mean=mean(x["utility"] for x in rs)
    distinct=len(set(x["worker_id"] for x in rs if x.get("worker_id")))
    by_worker=defaultdict(list)
    for x in rs:
        by_worker[x.get("worker_id")].append(x)
    for wid,wrs in sorted(by_worker.items()):
        if not wid: continue
        wruns=len(wrs)
        wdeep=sum(x["deep_inspected"] for x in wrs)
        wout=sum(1 for x in wrs if x["valid_outcome"])
        wmean=mean(x["utility"] for x in wrs)
        residual=wmean-baseline_mean
        evidence=(wruns/(wruns+prior))*((len(rs))/(len(rs)+prior))
        enough_activity=(wdeep>=min_worker_deep or wout>=min_worker_out)
        eligible=(
          global_n>=min_global and wruns>=min_worker_runs and len(rs)>=min_base and
          distinct>=min_workers and enough_activity and abs(residual)>=min_resid
        )
        raw=residual*scale*evidence if eligible else 0.0
        adj=max(-max_neg,min(max_pos,raw))
        adjustments.append({
          "worker_id":wid,"dimension":dim,"context_key":key,
          "worker_runs":wruns,"worker_deep_inspected":wdeep,"worker_valid_outcome_runs":wout,
          "baseline_runs":len(rs),"baseline_distinct_workers":distinct,
          "worker_mean_utility":round(wmean,6),"baseline_mean_utility":round(baseline_mean,6),
          "residual":round(residual,6),"evidence_weight":round(evidence,6),
          "adjustment":round(adj,4),"eligible_for_routing":bool(eligible),
          "evidence_state":"ELIGIBLE" if eligible else "INSUFFICIENT"
        })

def corr(pairs):
    if len(pairs)<2: return None
    xs=[float(a) for a,_ in pairs if a is not None]
    ys=[float(b) for a,b in pairs if a is not None]
    if len(xs)<2: return None
    mx,my=mean(xs),mean(ys)
    vx=sum((x-mx)**2 for x in xs); vy=sum((y-my)**2 for y in ys)
    if vx<=0 or vy<=0: return None
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(vx*vy)

calibration=[]
by_gen=defaultdict(list)
for r in learning_runs:
    if r.get("routing_generation_id"): by_gen[r["routing_generation_id"]].append(r)
for gid,rs in sorted(by_gen.items()):
    pairs=[(r.get("routing_score"),r["utility"]) for r in rs if isinstance(r.get("routing_score"),(int,float))]
    calibration.append({
      "routing_generation_id":gid,"completed_routes":len(rs),
      "mean_routing_score":round(mean([p[0] for p in pairs]),6) if pairs else None,
      "mean_realized_utility":round(mean([r["utility"] for r in rs]),6),
      "score_utility_correlation":None if len(pairs)<2 else (None if corr(pairs) is None else round(corr(pairs),6)),
      "calibration_evidence_state":"SUFFICIENT" if len(rs)>=int(POL.get("calibration_min_runs",8)) else "INSUFFICIENT"
    })

fingerprint=json.dumps({
  "policy":POL,
  "learning_runs":[(x["search_run_id"],x["worker_id"],x["utility"]) for x in learning_runs],
  "adjustments":[(x["worker_id"],x["dimension"],x["context_key"],x["adjustment"],x["eligible_for_routing"]) for x in adjustments]
},sort_keys=True)
generation="ROUTELEARN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in adjustments: x["routing_learning_generation_id"]=generation
for x in learning_runs: x["routing_learning_generation_id"]=generation

mode="adaptive" if any(x["eligible_for_routing"] for x in adjustments) else "observe_only_insufficient_evidence"
metrics={
  "schema_version":1,"routing_learning_generation_id":generation,"mode":mode,
  "generated_completed_routes":global_n,
  "eligible_adjustments":sum(1 for x in adjustments if x["eligible_for_routing"]),
  "adjustment_records":len(adjustments),
  "calibration_generations":len(calibration),
  "excluded_runs":excluded,
  "min_global_generated_completions":min_global
}

def write_jsonl(name,rows):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")

write_jsonl("routing_learning_runs.jsonl",learning_runs)
write_jsonl("routing_adjustments.jsonl",adjustments)
write_jsonl("routing_calibration.jsonl",calibration)
(INTEL/"routing_learning_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# ROUTING OUTCOME LEARNING REPORT","",f"Learning generation: **{generation}**",f"Mode: **{mode}**","",
f"- Completed generated routes eligible for learning: **{global_n}**",
f"- Adjustment records: **{len(adjustments)}**",
f"- Evidence-eligible routing adjustments: **{metrics['eligible_adjustments']}**","",
"Only completed MATCHED schema-v12+ generated routes train this learner. Manual overrides and retrospective repairs are excluded.","",
"## Eligible adjustments",""]
eligible_rows=[x for x in adjustments if x["eligible_for_routing"]]
if eligible_rows:
    report += ["| Worker | Dimension | Context | Runs | Residual | Weight | Adjustment |","|---|---|---|---:|---:|---:|---:|"]
    for x in sorted(eligible_rows,key=lambda x:-abs(x["adjustment"]))[:40]:
        report.append(f"| {x['worker_id']} | {x['dimension']} | {x['context_key']} | {x['worker_runs']} | {x['residual']:.3f} | {x['evidence_weight']:.3f} | {x['adjustment']:+.2f} |")
else:
    report.append("- None. Routing remains V12-only until enough generated-route evidence accumulates.")
report += ["","## Guardrails","",
"- Context baselines must include multiple workers and enough completed routes.",
"- A worker-context needs repeated runs plus either deep-inspection or outcome evidence.",
"- Learned adjustments are bounded and cannot erase assignment priority.",
"- Residuals are observational routing evidence, not causal worker rankings.",""]
(INTEL/"ROUTING_LEARNING_REPORT.md").write_text("\n".join(report),encoding="utf-8")

calrep=["# ROUTING CALIBRATION REPORT","",f"Learning generation: **{generation}**","",
"Routing-score calibration is descriptive. It does not estimate causal regret.","",
"| Routing generation | Completed routes | Mean routing score | Mean realized utility | Score↔utility correlation | Evidence |",
"|---|---:|---:|---:|---:|---|"]
for x in calibration:
    corr_text="—" if x["score_utility_correlation"] is None else f"{x['score_utility_correlation']:.3f}"
    score_text="—" if x["mean_routing_score"] is None else f"{x['mean_routing_score']:.3f}"
    calrep.append(f"| {x['routing_generation_id']} | {x['completed_routes']} | {score_text} | {x['mean_realized_utility']:.3f} | {corr_text} | {x['calibration_evidence_state']} |")
if not calibration:
    calrep.append("| — | 0 | — | — | — | INSUFFICIENT |")
calrep += ["","A true counterfactual-regret estimate requires preserving alternate feasible matchings at routing time; V13 deliberately does not invent one.",""]
(INTEL/"ROUTING_CALIBRATION_REPORT.md").write_text("\n".join(calrep),encoding="utf-8")
print(json.dumps(metrics))
