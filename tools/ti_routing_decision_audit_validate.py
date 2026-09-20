#!/usr/bin/env python3
import json
from functools import lru_cache
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_decision_policy.json").read_text(encoding="utf-8"))
CAND=load_jsonl("routing_candidates.jsonl")
ROUTES=load_jsonl("worker_routing.jsonl")
AUD=load_jsonl("routing_decision_audit.jsonl")
SUM=json.loads((INTEL/"routing_generation_audit.json").read_text(encoding="utf-8"))
tol=float(POL.get("score_tolerance",1e-6))

edges={(x["worker_id"],x["slot_id"]):x for x in CAND}
workers=sorted(set(x["worker_id"] for x in CAND))
slots=sorted(set(x["slot_id"] for x in CAND))
routed=[r for r in ROUTES if r.get("route_status")=="ROUTED"]
chosen={(r["worker_id"],r["slot_id"]):r for r in routed}

if len(AUD)!=len(routed): raise SystemExit("routing decision audit count drift")
if len({x["decision_id"] for x in AUD})!=len(AUD): raise SystemExit("duplicate routing decision_id")
if set((x["worker_id"],x["slot_id"]) for x in AUD)!=set(chosen): raise SystemExit("audit pair coverage drift")
if SUM.get("routed_pairs")!=len(routed): raise SystemExit("routing generation audit routed_pairs drift")

def solve(forbidden=None):
    forbidden=set(forbidden or [])
    if len(workers)<=len(slots):
        @lru_cache(None)
        def dp(i,mask):
            if i==len(workers): return (0.0,())
            wid=workers[i]; best=(-1e100,())
            for j,slot in enumerate(slots):
                if mask&(1<<j) or (wid,slot) in forbidden: continue
                e=edges.get((wid,slot))
                if not e: continue
                tail,path=dp(i+1,mask|(1<<j))
                if tail<-1e90: continue
                val=float(e["routing_score"])+tail
                cand=(val,(slot,)+path)
                if val>best[0]+tol or (abs(val-best[0])<=tol and cand[1]<best[1]): best=cand
            return best
        val,path=dp(0,0)
        if val<-1e90:return None,None
        return val,[(workers[i],path[i]) for i in range(len(workers))]
    @lru_cache(None)
    def dp(i,mask):
        if i==len(slots): return (0.0,())
        slot=slots[i]; best=(-1e100,())
        for j,wid in enumerate(workers):
            if mask&(1<<j) or (wid,slot) in forbidden: continue
            e=edges.get((wid,slot))
            if not e: continue
            tail,path=dp(i+1,mask|(1<<j))
            if tail<-1e90: continue
            val=float(e["routing_score"])+tail
            cand=(val,(wid,)+path)
            if val>best[0]+tol or (abs(val-best[0])<=tol and cand[1]<best[1]): best=cand
        return best
    val,path=dp(0,0)
    if val<-1e90:return None,None
    return val,[(path[i],slots[i]) for i in range(len(slots))]

opt,opt_pairs=solve()
if opt is None: raise SystemExit("no feasible full matching in validator")
if abs(float(SUM.get("global_optimal_score"))-opt)>tol: raise SystemExit("summary global optimum drift")
chosen_total=sum(float(edges[k]["routing_score"]) for k in chosen)
if abs(float(SUM.get("chosen_total_score"))-chosen_total)>tol: raise SystemExit("summary chosen total drift")
if abs(chosen_total-opt)>tol: raise SystemExit("current routed assignment is not globally optimal")

audit_gen=SUM.get("routing_decision_audit_generation_id")
for n,x in enumerate(AUD,1):
    if x.get("routing_decision_audit_generation_id")!=audit_gen: raise SystemExit(f"routing_decision_audit.jsonl:{n}: generation drift")
    pair=(x["worker_id"],x["slot_id"])
    if pair not in edges: raise SystemExit(f"routing_decision_audit.jsonl:{n}: unknown chosen edge")
    if abs(float(x["chosen_score"])-float(edges[pair]["routing_score"]))>tol: raise SystemExit(f"routing_decision_audit.jsonl:{n}: chosen score drift")
    alt,alt_pairs=solve({pair})
    if alt is None:
        if x.get("counterfactual_feasible"): raise SystemExit(f"routing_decision_audit.jsonl:{n}: claims infeasible counterfactual is feasible")
        if x.get("global_alternative_score_without_pair") is not None or x.get("global_pair_criticality") is not None:
            raise SystemExit(f"routing_decision_audit.jsonl:{n}: infeasible counterfactual has numeric score")
    else:
        if not x.get("counterfactual_feasible"): raise SystemExit(f"routing_decision_audit.jsonl:{n}: feasible counterfactual marked false")
        if abs(float(x["global_alternative_score_without_pair"])-alt)>tol: raise SystemExit(f"routing_decision_audit.jsonl:{n}: alternative score drift")
        crit=opt-alt
        if crit<-tol: raise SystemExit(f"routing_decision_audit.jsonl:{n}: negative global criticality")
        if abs(float(x["global_pair_criticality"])-max(0.0,crit))>tol: raise SystemExit(f"routing_decision_audit.jsonl:{n}: criticality drift")
        pairs=[(p["worker_id"],p["slot_id"]) for p in x.get("counterfactual_pairs") or []]
        if pair in pairs: raise SystemExit(f"routing_decision_audit.jsonl:{n}: forbidden pair appears in counterfactual")
        if sorted(pairs)!=sorted(alt_pairs): raise SystemExit(f"routing_decision_audit.jsonl:{n}: counterfactual pair set drift")
        if len({p[0] for p in pairs})!=len(pairs) or len({p[1] for p in pairs})!=len(pairs):
            raise SystemExit(f"routing_decision_audit.jsonl:{n}: duplicate worker/slot in counterfactual")
print(f"OK routed={len(routed)} candidates={len(CAND)} optimum={opt:.4f} audit={audit_gen}")
