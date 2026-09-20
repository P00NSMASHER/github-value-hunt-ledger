#!/usr/bin/env python3
import hashlib, json, re
from collections import defaultdict
from ti_common import INTEL, load_jsonl

REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
ALIASES=json.loads((INTEL/"worker_aliases.json").read_text(encoding="utf-8")).get("aliases",{})
POLICY=json.loads((INTEL/"routing_policy.json").read_text(encoding="utf-8"))
RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
CLAIMS=load_jsonl("execution_claim_history.jsonl") if (INTEL/"execution_claim_history.jsonl").exists() else []
OUTCOMES=load_jsonl("outcomes.jsonl") if (INTEL/"outcomes.jsonl").exists() else []

worker_ids={w["worker_id"] for w in REG["workers"]}

def canonical_worker(r):
    ew=r.get("execution_worker_id")
    if ew in worker_ids:
        return ew
    label=r.get("hunter_role") or r.get("hunter") or ""
    if label in ALIASES:
        return ALIASES[label]
    candidates=[
      re.search(r"\bNODE\s*0*(\d{1,2})\b",label,re.I),
      re.search(r"\bHunt\s*0*(\d{1,2})\b",label,re.I),
      re.search(r"\bHUNTER[-_\s]?0*(\d{1,2})\b",label,re.I),
      re.search(r"\bhunter0*(\d{1,2})\b",str(r.get("search_run_id") or ""),re.I),
      re.search(r"\bRUN:H0*(\d{1,2})-",str(r.get("search_run_id") or ""),re.I)
    ]
    for m in candidates:
        if m:
            n=int(m.group(1))
            wid=f"HUNTER-{n:02d}"
            if wid in worker_ids:
                return wid
    return None

outcomes_by_run=defaultdict(list)
for o in OUTCOMES:
    if o.get("result")=="INVALID": continue
    for rid in o.get("origin_search_ids") or []:
        outcomes_by_run[rid].append(o)

def empty(worker_id):
    return {
      "worker_id":worker_id,"status":"active","historical_runs":0,"deep_inspected":0,
      "retained_count":0,"master_promoted_count":0,"new_capability_count":0,
      "experiment_touch_runs":0,"valid_outcome_runs":0,"passed_outcome_runs":0,
      "strategy_counts":defaultdict(int),"objective_counts":defaultdict(int),
      "experiment_counts":defaultdict(int),"capability_counts":defaultdict(int),
      "domain_counts_map":defaultdict(int),"claim_role_counts":defaultdict(int),
      "active_claims":0,"completed_claims":0,"failed_claims":0
    }

profiles={w["worker_id"]:empty(w["worker_id"]) for w in REG["workers"]}
for w in REG["workers"]:
    profiles[w["worker_id"]]["status"]=w.get("status","active")

unmapped=[]
mapped_run_ids=set()
for r in RUNS:
    wid=canonical_worker(r)
    if not wid:
        unmapped.append({
          "search_run_id":r.get("search_run_id"),
          "hunter_label":r.get("hunter_role") or r.get("hunter"),
          "strategy_id":r.get("strategy_id")
        })
        continue
    mapped_run_ids.add(r.get("search_run_id"))
    p=profiles[wid]
    p["historical_runs"]+=1
    p["deep_inspected"]+=int(r.get("deep_inspected") or 0)
    p["retained_count"]+=int(r.get("retained_count") or 0)
    p["master_promoted_count"]+=int(r.get("master_promoted_count") or 0)
    p["new_capability_count"]+=len(r.get("new_capability_ids") or [])
    p["experiment_touch_runs"]+=1 if (r.get("experiment_ids") or []) else 0
    if outcomes_by_run.get(r.get("search_run_id")):
        p["valid_outcome_runs"]+=1
        if any(o.get("result")=="PASSED" for o in outcomes_by_run[r.get("search_run_id")]):
            p["passed_outcome_runs"]+=1
    sid=r.get("strategy_id")
    if sid: p["strategy_counts"][sid]+=1
    oid=r.get("search_objective_id")
    if oid: p["objective_counts"][oid]+=1
    for eid in r.get("experiment_ids") or []:
        p["experiment_counts"][eid]+=1
        p["domain_counts_map"]["EXP:"+eid]+=1
    caps=set((r.get("new_capability_ids") or [])+(r.get("strengthened_capability_ids") or []))
    for cid in caps: p["capability_counts"][cid]+=1
    for lane in r.get("lane_ids") or []:
        if not re.match(r"^NODE-\d+$",lane,re.I):
            p["domain_counts_map"][lane]+=1

for c in CLAIMS:
    wid=c.get("worker_id")
    if wid not in profiles: continue
    p=profiles[wid]
    role=c.get("assignment_slot_role")
    if role: p["claim_role_counts"][role]+=1
    st=c.get("status")
    if st in {"CLAIMED","RUNNING"}: p["active_claims"]+=1
    elif st=="COMPLETE": p["completed_claims"]+=1
    elif st in {"FAILED_TERMINAL","FAILED_RETRYABLE"}: p["failed_claims"]+=1

def sorted_counts(d):
    return [{"key":k,"count":v} for k,v in sorted(d.items(),key=lambda kv:(-kv[1],kv[0]))]

rows=[]
for wid in sorted(profiles):
    p=profiles[wid]
    runs=p["historical_runs"]; deep=p["deep_inspected"]
    if runs>=int(POLICY.get("min_runs_for_measured_label",3)) and deep>=int(POLICY.get("min_deep_for_measured_label",6)):
        measured="MEASURED"
    elif runs>0 or p["active_claims"] or p["completed_claims"]:
        measured="SPARSE"
    else:
        measured="UNMEASURED"
    retained_precision=(p["retained_count"]/deep) if deep else None
    performance_signal=0.0
    if runs:
        perf_evidence=runs/(runs+5)
        performance_signal=perf_evidence*(
          .50*(retained_precision or 0)+
          .20*min(1,p["master_promoted_count"]/runs)+
          .15*min(1,p["new_capability_count"]/runs)+
          .15*min(1,p["valid_outcome_runs"]/runs)
        )
    row={
      "worker_id":wid,"status":p["status"],"historical_runs":runs,"deep_inspected":deep,
      "retained_count":p["retained_count"],"master_promoted_count":p["master_promoted_count"],
      "new_capability_count":p["new_capability_count"],"experiment_touch_runs":p["experiment_touch_runs"],
      "valid_outcome_runs":p["valid_outcome_runs"],"passed_outcome_runs":p["passed_outcome_runs"],
      "retained_precision":retained_precision,"performance_signal":round(performance_signal,4),
      "measured_state":measured,
      "strategy_counts":dict(p["strategy_counts"]),"objective_counts":dict(p["objective_counts"]),
      "experiment_counts":dict(p["experiment_counts"]),"capability_counts":dict(p["capability_counts"]),
      "domain_counts_raw":dict(p["domain_counts_map"]),"claim_role_counts":dict(p["claim_role_counts"]),
      "top_strategies":sorted_counts(p["strategy_counts"])[:5],
      "top_objectives":sorted_counts(p["objective_counts"])[:5],
      "top_experiments":sorted_counts(p["experiment_counts"])[:5],
      "top_capabilities":sorted_counts(p["capability_counts"])[:6],
      "domain_counts":sorted_counts(p["domain_counts_map"])[:8],
      "active_claims":p["active_claims"],"completed_claims":p["completed_claims"],"failed_claims":p["failed_claims"]
    }
    rows.append(row)

fingerprint=json.dumps({
  "workers":[(x["worker_id"],x["historical_runs"],x["deep_inspected"],x["strategy_counts"],x["experiment_counts"],x["capability_counts"],x["claim_role_counts"]) for x in rows],
  "mapped_runs":sorted(x for x in mapped_run_ids if x)
},sort_keys=True)
generation="WORKERS:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in rows: x["worker_profile_generation_id"]=generation

(INTEL/"worker_profiles.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
(INTEL/"worker_unmapped_runs.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in unmapped)+("\n" if unmapped else ""),encoding="utf-8")

triples=defaultdict(lambda:{"runs":0,"deep_inspected":0,"retained_count":0,"master_promoted_count":0,"new_capability_runs":0,"experiment_touch_runs":0})
for r in RUNS:
    wid=canonical_worker(r)
    if not wid: continue
    sid=r.get("strategy_id") or "STRAT:unknown"
    domains=[x for x in (r.get("lane_ids") or []) if not re.match(r"^NODE-\d+$",x,re.I)]
    domains += ["EXP:"+x for x in (r.get("experiment_ids") or [])]
    if not domains: domains=["DOMAIN:unknown"]
    for d in sorted(set(domains)):
        t=triples[(wid,sid,d)]
        t["runs"]+=1;t["deep_inspected"]+=int(r.get("deep_inspected") or 0);t["retained_count"]+=int(r.get("retained_count") or 0)
        t["master_promoted_count"]+=int(r.get("master_promoted_count") or 0)
        t["new_capability_runs"]+=1 if (r.get("new_capability_ids") or []) else 0
        t["experiment_touch_runs"]+=1 if (r.get("experiment_ids") or []) else 0
triple_rows=[]
for (wid,sid,d),v in sorted(triples.items()):
    triple_rows.append({"worker_id":wid,"strategy_id":sid,"domain_key":d,**v,
      "retained_precision":(v["retained_count"]/v["deep_inspected"]) if v["deep_inspected"] else None})
(INTEL/"worker_strategy_domain_metrics.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in triple_rows)+("\n" if triple_rows else ""),encoding="utf-8")

metrics={
  "schema_version":1,"worker_profile_generation_id":generation,"registered_workers":len(rows),
  "measured_workers":sum(1 for x in rows if x["measured_state"]=="MEASURED"),
  "sparse_workers":sum(1 for x in rows if x["measured_state"]=="SPARSE"),
  "unmeasured_workers":sum(1 for x in rows if x["measured_state"]=="UNMEASURED"),
  "mapped_runs":len(mapped_run_ids),"unmapped_runs":len(unmapped),
  "active_claim_workers":sum(1 for x in rows if x["active_claims"]>0)
}
(INTEL/"worker_profile_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# WORKER PROFILE REPORT","",f"Profile generation: **{generation}**","",
f"- Registered workers: **{len(rows)}**",f"- Measured: **{metrics['measured_workers']}**",f"- Sparse: **{metrics['sparse_workers']}**",f"- Unmeasured: **{metrics['unmeasured_workers']}**",f"- Unmapped historical runs: **{len(unmapped)}**","",
"| Worker | State | Runs | Deep | Retained | Top strategy | Top experiment | Active claim |",
"|---|---|---:|---:|---:|---|---|---:|"]
for x in rows:
    ts=x["top_strategies"][0]["key"] if x["top_strategies"] else "—"
    te=x["top_experiments"][0]["key"] if x["top_experiments"] else "—"
    report.append(f"| {x['worker_id']} | {x['measured_state']} | {x['historical_runs']} | {x['deep_inspected']} | {x['retained_count']} | {ts} | {te} | {x['active_claims']} |")
report += ["","## Interpretation","",
"- Historical match evidence can raise routing fit; missing evidence never lowers a worker below an equally suitable unmeasured worker.",
"- Worker performance signals are intentionally small and shrink heavily with sparse data.",
"- Strategy/domain metrics are observational and confounded by task selection.",
"- V11 active claims are capacity locks, not evidence of worker quality.",""]
(INTEL/"WORKER_PROFILE_REPORT.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
