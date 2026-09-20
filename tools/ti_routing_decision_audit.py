#!/usr/bin/env python3
import hashlib, json
from functools import lru_cache
from statistics import mean
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_decision_policy.json").read_text(encoding="utf-8"))
CAND=load_jsonl("routing_candidates.jsonl")
ROUTES=load_jsonl("worker_routing.jsonl")
MET=json.loads((INTEL/"routing_metrics.json").read_text(encoding="utf-8"))

tol=float(POL.get("score_tolerance",1e-6))
edges={(x["worker_id"],x["slot_id"]):x for x in CAND}
workers=sorted(set(x["worker_id"] for x in CAND))
slots=sorted(set(x["slot_id"] for x in CAND))
chosen=[r for r in ROUTES if r.get("route_status")=="ROUTED"]

def solve(forbidden=None):
    forbidden=set(forbidden or [])
    if not workers or not slots:
        return 0.0,[]
    if len(workers)<=len(slots):
        if len(slots)>int(POL.get("max_exact_workers",16)): raise SystemExit("too many slots for exact audit")
        @lru_cache(None)
        def dp(i,mask):
            if i==len(workers): return (0.0,())
            wid=workers[i]
            best=(-1e100,())
            for j,slot in enumerate(slots):
                if mask&(1<<j): continue
                if (wid,slot) in forbidden: continue
                e=edges.get((wid,slot))
                if not e: continue
                tail,path=dp(i+1,mask|(1<<j))
                if tail<-1e90: continue
                val=float(e["routing_score"])+tail
                cand=(val,(slot,)+path)
                if val>best[0]+tol or (abs(val-best[0])<=tol and cand[1]<best[1]):
                    best=cand
            return best
        val,path=dp(0,0)
        if val<-1e90: return None,None
        return val,[(workers[i],path[i]) for i in range(len(workers))]
    else:
        if len(workers)>int(POL.get("max_exact_workers",16)): raise SystemExit("too many workers for exact audit")
        @lru_cache(None)
        def dp(i,mask):
            if i==len(slots): return (0.0,())
            slot=slots[i]
            best=(-1e100,())
            for j,wid in enumerate(workers):
                if mask&(1<<j): continue
                if (wid,slot) in forbidden: continue
                e=edges.get((wid,slot))
                if not e: continue
                tail,path=dp(i+1,mask|(1<<j))
                if tail<-1e90: continue
                val=float(e["routing_score"])+tail
                cand=(val,(wid,)+path)
                if val>best[0]+tol or (abs(val-best[0])<=tol and cand[1]<best[1]):
                    best=cand
            return best
        val,path=dp(0,0)
        if val<-1e90: return None,None
        return val,[(path[i],slots[i]) for i in range(len(slots))]

opt_score,opt_pairs=solve()
if opt_score is None: raise SystemExit("routing candidate graph has no full feasible matching")
chosen_pairs=sorted((r["worker_id"],r["slot_id"]) for r in chosen)
if sorted(opt_pairs)!=chosen_pairs:
    chosen_total=sum(float(edges[(w,s)]["routing_score"]) for w,s in chosen_pairs)
    if abs(chosen_total-opt_score)>tol:
        raise SystemExit(f"chosen routing is not globally optimal: chosen={chosen_total} optimum={opt_score}")

chosen_total=sum(float(edges[(w,s)]["routing_score"]) for w,s in chosen_pairs)
if abs(chosen_total-opt_score)>tol:
    raise SystemExit("chosen route total drift from recomputed optimum")

worker_edges={}
slot_edges={}
for e in CAND:
    worker_edges.setdefault(e["worker_id"],[]).append(e)
    slot_edges.setdefault(e["slot_id"],[]).append(e)
for vals in worker_edges.values(): vals.sort(key=lambda x:(-float(x["routing_score"]),x["slot_id"]))
for vals in slot_edges.values(): vals.sort(key=lambda x:(-float(x["routing_score"]),x["worker_id"]))

rows=[]
for r in sorted(chosen,key=lambda x:x["worker_id"]):
    wid,slot=r["worker_id"],r["slot_id"]
    e=edges[(wid,slot)]
    alt_score,alt_pairs=solve({(wid,slot)})
    feasible=alt_score is not None
    criticality=None if not feasible else max(0.0,opt_score-alt_score)
    wvals=worker_edges[wid]
    svals=slot_edges[slot]
    walt=next((x for x in wvals if x["slot_id"]!=slot),None)
    salt=next((x for x in svals if x["worker_id"]!=wid),None)
    wrank=next(i+1 for i,x in enumerate(wvals) if x["slot_id"]==slot)
    srank=next(i+1 for i,x in enumerate(svals) if x["worker_id"]==wid)
    seed=f"{MET.get('routing_generation_id')}|{wid}|{slot}|{r.get('assignment_id')}"
    rows.append({
      "decision_id":"ROUTEDEC:"+hashlib.sha256(seed.encode()).hexdigest()[:12],
      "routing_generation_id":MET.get("routing_generation_id"),
      "worker_profile_generation_id":MET.get("worker_profile_generation_id"),
      "routing_learning_generation_id":MET.get("routing_learning_generation_id"),
      "worker_id":wid,"slot_id":slot,"assignment_id":r.get("assignment_id"),
      "chosen_score":round(float(e["routing_score"]),6),
      "global_optimal_score":round(opt_score,6),
      "global_alternative_score_without_pair":None if not feasible else round(alt_score,6),
      "global_pair_criticality":None if criticality is None else round(criticality,6),
      "counterfactual_feasible":bool(feasible),
      "counterfactual_pairs":[] if not feasible else [
        {"worker_id":w,"slot_id":s,"routing_score":round(float(edges[(w,s)]["routing_score"]),6)}
        for w,s in alt_pairs
      ],
      "worker_next_best_slot":None if not walt else walt["slot_id"],
      "worker_next_best_score":None if not walt else round(float(walt["routing_score"]),6),
      "worker_local_delta":None if not walt else round(float(e["routing_score"])-float(walt["routing_score"]),6),
      "slot_next_best_worker":None if not salt else salt["worker_id"],
      "slot_next_best_score":None if not salt else round(float(salt["routing_score"]),6),
      "slot_local_delta":None if not salt else round(float(e["routing_score"])-float(salt["routing_score"]),6),
      "worker_candidate_count":len(wvals),"slot_candidate_count":len(svals),
      "worker_score_rank":wrank,"slot_score_rank":srank
    })

fingerprint=json.dumps({
  "routing_generation":MET.get("routing_generation_id"),
  "chosen_pairs":chosen_pairs,
  "optimal_score":round(opt_score,6),
  "rows":[(x["decision_id"],x["global_pair_criticality"],x["counterfactual_feasible"]) for x in rows]
},sort_keys=True)
audit_gen="ROUTEAUDIT:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in rows: x["routing_decision_audit_generation_id"]=audit_gen

summary={
  "schema_version":1,
  "routing_decision_audit_generation_id":audit_gen,
  "routing_generation_id":MET.get("routing_generation_id"),
  "worker_profile_generation_id":MET.get("worker_profile_generation_id"),
  "routing_learning_generation_id":MET.get("routing_learning_generation_id"),
  "routed_pairs":len(rows),
  "candidate_edges":len(CAND),
  "global_optimal_score":round(opt_score,6),
  "chosen_total_score":round(chosen_total,6),
  "zero_criticality_pairs":sum(1 for x in rows if x["counterfactual_feasible"] and abs(x["global_pair_criticality"] or 0)<=tol),
  "no_full_counterfactual_pairs":sum(1 for x in rows if not x["counterfactual_feasible"]),
  "mean_pair_criticality":round(mean([x["global_pair_criticality"] for x in rows if x["global_pair_criticality"] is not None]),6) if any(x["global_pair_criticality"] is not None for x in rows) else None
}

(INTEL/"routing_decision_audit.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")
(INTEL/"routing_generation_audit.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")

report=["# ROUTING DECISION AUDIT","",f"Audit generation: **{audit_gen}**",f"Routing generation: **{summary['routing_generation_id']}**","",
f"- Routed pairs audited: **{summary['routed_pairs']}**",
f"- Candidate worker↔slot edges: **{summary['candidate_edges']}**",
f"- Global optimal routing score: **{summary['global_optimal_score']:.3f}**",
f"- Zero-criticality chosen pairs: **{summary['zero_criticality_pairs']}**",
f"- Chosen pairs with no full counterfactual matching: **{summary['no_full_counterfactual_pairs']}**","",
"Pair criticality is the loss in total routing score when that exact chosen pair is forbidden and the remaining routing problem is fully re-optimized.","",
"| Worker | Slot | Chosen | Global criticality | Worker next-best | Worker Δ | Slot next-best | Slot Δ |",
"|---|---|---:|---:|---|---:|---|---:|"]
for x in rows:
    crit="—" if x["global_pair_criticality"] is None else f"{x['global_pair_criticality']:.3f}"
    walt="—" if x["worker_next_best_slot"] is None else f"{x['worker_next_best_slot']} ({x['worker_next_best_score']:.2f})"
    wdel="—" if x["worker_local_delta"] is None else f"{x['worker_local_delta']:+.2f}"
    salt="—" if x["slot_next_best_worker"] is None else f"{x['slot_next_best_worker']} ({x['slot_next_best_score']:.2f})"
    sdel="—" if x["slot_local_delta"] is None else f"{x['slot_local_delta']:+.2f}"
    report.append(f"| {x['worker_id']} | {x['slot_id']} | {x['chosen_score']:.2f} | {crit} | {walt} | {wdel} | {salt} | {sdel} |")
report += ["","## Interpretation","",
"- A zero-criticality pair can be removed without reducing the globally optimized routing score; it is a natural future exploration candidate.",
"- A negative local delta is not an error: global assignment constraints can make a locally lower-scoring edge part of the best overall matching.",
"- V14 records alternatives only. It does not reroute workers or claim causal regret.",""]
(INTEL/"ROUTING_DECISION_AUDIT.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(summary))
