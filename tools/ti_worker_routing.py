#!/usr/bin/env python3
import hashlib, json
from functools import lru_cache
from ti_common import INTEL, load_jsonl

REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
POL=json.loads((INTEL/"routing_policy.json").read_text(encoding="utf-8"))
PROFILES={x["worker_id"]:x for x in load_jsonl("worker_profiles.jsonl")}
P_MET=json.loads((INTEL/"worker_profile_metrics.json").read_text(encoding="utf-8"))
LEARN_POL=json.loads((INTEL/"routing_learning_policy.json").read_text(encoding="utf-8")) if (INTEL/"routing_learning_policy.json").exists() else {}
LEARN_MET=json.loads((INTEL/"routing_learning_metrics.json").read_text(encoding="utf-8")) if (INTEL/"routing_learning_metrics.json").exists() else {}
ADJUSTMENTS=load_jsonl("routing_adjustments.jsonl") if (INTEL/"routing_adjustments.jsonl").exists() else []
RESPONSE_MET=json.loads((INTEL/"activation_response_metrics.json").read_text(encoding="utf-8")) if (INTEL/"activation_response_metrics.json").exists() else {}
RESPONSE_ADJUSTMENTS=load_jsonl("activation_response_adjustments.jsonl") if (INTEL/"activation_response_adjustments.jsonl").exists() else []
ALLOC=load_jsonl("hunt_allocations.jsonl")
STATE=load_jsonl("execution_state.jsonl")

alloc_by_slot={x["slot_id"]:x for x in ALLOC}
state_by_slot={x["slot_id"]:x for x in STATE}
workers=[w for w in REG["workers"]]
registered={w["worker_id"] for w in workers}
claimable=set(POL.get("allowed_claimable_states") or [])
LEARN_GEN=LEARN_MET.get("routing_learning_generation_id") or "ROUTELEARN:000000000000"
ADJ_INDEX={(x.get("worker_id"),x.get("dimension"),x.get("context_key")):x for x in ADJUSTMENTS if x.get("eligible_for_routing")}
RESPONSE_GEN=RESPONSE_MET.get("response_learning_generation_id") or "RESPLEARN:000000000000"
RESPONSE_INDEX={x.get("worker_id"):x for x in RESPONSE_ADJUSTMENTS if x.get("eligible_for_routing")}

def support_bonus(count,weight):
    k=float(POL.get("support_shrinkage_k",3))
    return weight*(count/(count+k)) if count else 0.0

def assignment_domains(a):
    out=["EXP:"+e for e in a.get("experiment_ids") or []]
    if a.get("search_objective_id"): out.append(a["search_objective_id"])
    return out

def learning_contexts(a):
    out=[]
    for dim,key in [
      ("role",a.get("slot_role")),
      ("work_kind",a.get("work_kind")),
      ("strategy",a.get("strategy_id")),
      ("objective",a.get("search_objective_id"))
    ]:
        if key: out.append((dim,key))
    for e in sorted(set(a.get("experiment_ids") or [])):
        out.append(("experiment",e))
    return out

def learned_adjustment(worker_id,a):
    rows=[]
    for dim,key in learning_contexts(a):
        x=ADJ_INDEX.get((worker_id,dim,key))
        if x: rows.append(x)
    if not rows:
        return 0.0,0
    total_w=sum(float(x.get("evidence_weight") or 0) for x in rows)
    if total_w<=0:
        return 0.0,0
    raw=sum(float(x.get("adjustment") or 0)*float(x.get("evidence_weight") or 0) for x in rows)/total_w
    max_pos=float(LEARN_POL.get("max_positive_adjustment",3.0))
    max_neg=float(LEARN_POL.get("max_negative_adjustment",2.0))
    return round(max(-max_neg,min(max_pos,raw)),4),len(rows)

def score(worker_id,a):
    p=PROFILES[worker_id]
    comp={}
    comp["assignment_priority"]=float(a.get("final_score") or 0)*float(POL.get("assignment_priority_weight",0.12))
    comp["strategy_fit"]=support_bonus((p.get("strategy_counts") or {}).get(a.get("strategy_id"),0),float(POL.get("strategy_fit_weight",8))) if a.get("strategy_id") else 0.0
    comp["objective_fit"]=support_bonus((p.get("objective_counts") or {}).get(a.get("search_objective_id"),0),float(POL.get("objective_fit_weight",5))) if a.get("search_objective_id") else 0.0
    exp_support=max([(p.get("experiment_counts") or {}).get(e,0) for e in a.get("experiment_ids") or []] or [0])
    cap_support=max([(p.get("capability_counts") or {}).get(c,0) for c in a.get("capability_ids") or []] or [0])
    dom_support=max([(p.get("domain_counts_raw") or {}).get(d,0) for d in assignment_domains(a)] or [0])
    role_support=(p.get("claim_role_counts") or {}).get(a.get("slot_role"),0)
    comp["experiment_fit"]=support_bonus(exp_support,float(POL.get("experiment_fit_weight",10)))
    comp["capability_fit"]=support_bonus(cap_support,float(POL.get("capability_fit_weight",8)))
    comp["domain_fit"]=support_bonus(dom_support,float(POL.get("domain_fit_weight",5)))
    comp["role_experience"]=support_bonus(role_support,float(POL.get("role_experience_weight",4)))
    comp["performance"]=float(POL.get("performance_weight",3))*float(p.get("performance_signal") or 0)
    runs=int(p.get("historical_runs") or 0)
    comp["exploration_bonus"]=float(POL.get("unmeasured_exploration_bonus",4))/(1+runs)
    learned,evidence_count=learned_adjustment(worker_id,a)
    comp["routing_learning"]=learned
    comp["activation_response"]=float((RESPONSE_INDEX.get(worker_id) or {}).get("routing_response_adjustment") or 0)
    total=sum(comp.values())
    return round(total,4),{k:round(v,4) for k,v in comp.items()},evidence_count

active_by_worker={}
locked=[]
for s in STATE:
    if s.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}:
        wid=s.get("worker_id")
        if wid:
            active_by_worker[wid]=s
            a=alloc_by_slot.get(s["slot_id"])
            locked.append({
              "worker_id":wid,"slot_id":s["slot_id"],"assignment_id":s.get("claimed_assignment_id") or (a or {}).get("assignment_id"),
              "work_item_id":(a or {}).get("work_item_id"),"claim_id":s.get("claim_id"),
              "routing_score":None,"score_components":{},"evidence_state":"LOCKED_ACTIVE_CLAIM",
              "route_status":"LOCKED","reason":"Existing V11 active claim is authoritative and cannot be rerouted."
            })

eligible=[w for w in workers if w.get("status","active")=="active" and w["worker_id"] not in active_by_worker]
available_slots=[s["slot_id"] for s in STATE if s.get("status") in claimable]
available_slots=[s for s in available_slots if s in alloc_by_slot]

edges=[]
for w in eligible:
    wid=w["worker_id"]
    allowed=set(w.get("allowed_slot_roles") or [])
    for slot in available_slots:
        a=alloc_by_slot[slot]
        if allowed and a.get("slot_role") not in allowed: continue
        sc,comp,learn_count=score(wid,a)
        edges.append({
          "worker_id":wid,"slot_id":slot,"assignment_id":a["assignment_id"],"work_item_id":a["work_item_id"],
          "source_id":a.get("source_id"),"slot_role":a.get("slot_role"),"work_kind":a.get("work_kind"),
          "strategy_id":a.get("strategy_id"),"search_objective_id":a.get("search_objective_id"),
          "routing_score":sc,"score_components":comp,
          "routing_learning_generation_id":LEARN_GEN,
          "activation_response_learning_generation_id":RESPONSE_GEN,
          "routing_learning_evidence_count":learn_count,
          "worker_evidence_state":PROFILES[wid].get("measured_state")
        })

edge_map={(e["worker_id"],e["slot_id"]):e for e in edges}
worker_ids=[w["worker_id"] for w in eligible]
slot_ids=list(available_slots)

def exact_assign(workers,slots):
    if not workers or not slots: return []
    # Assign every member of the smaller side exactly once, choosing distinct counterparts.
    if len(workers)<=len(slots):
        if len(slots)>int(POL.get("exact_match_max_workers",16)): raise SystemExit("too many slots for exact matcher")
        @lru_cache(None)
        def dp(i,mask):
            if i==len(workers): return (0.0,())
            wid=workers[i]
            best=(-1e18,())
            for j,slot in enumerate(slots):
                if mask&(1<<j): continue
                e=edge_map.get((wid,slot))
                if not e: continue
                tail,path=dp(i+1,mask|(1<<j))
                val=e["routing_score"]+tail
                cand=(val,(slot,)+path)
                if val>best[0]+1e-12 or (abs(val-best[0])<=1e-12 and cand[1]<best[1]):
                    best=cand
            return best
        val,path=dp(0,0)
        if val<-1e17: return []
        return [(workers[i],path[i]) for i in range(len(workers))]
    else:
        if len(workers)>int(POL.get("exact_match_max_workers",16)): raise SystemExit("too many workers for exact matcher")
        @lru_cache(None)
        def dp(i,mask):
            if i==len(slots): return (0.0,())
            slot=slots[i]
            best=(-1e18,())
            for j,wid in enumerate(workers):
                if mask&(1<<j): continue
                e=edge_map.get((wid,slot))
                if not e: continue
                tail,path=dp(i+1,mask|(1<<j))
                val=e["routing_score"]+tail
                cand=(val,(wid,)+path)
                if val>best[0]+1e-12 or (abs(val-best[0])<=1e-12 and cand[1]<best[1]):
                    best=cand
            return best
        val,path=dp(0,0)
        if val<-1e17: return []
        return [(path[i],slots[i]) for i in range(len(slots))]

pairs=exact_assign(worker_ids,slot_ids)
pair_map={wid:slot for wid,slot in pairs}
used_slots=set(pair_map.values())

fingerprint=json.dumps({
  "profile_generation":P_MET.get("worker_profile_generation_id"),
  "routing_learning_generation":LEARN_GEN,
  "activation_response_learning_generation":RESPONSE_GEN,
  "state":[(x.get("slot_id"),x.get("status"),x.get("worker_id"),x.get("current_assignment_id")) for x in STATE],
  "alloc":[(x["slot_id"],x["assignment_id"],x.get("final_score")) for x in ALLOC],
  "routes":sorted(pairs)
},sort_keys=True)
routing_generation="ROUTING:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
profile_generation=P_MET["worker_profile_generation_id"]

routes=[]
for w in workers:
    wid=w["worker_id"]
    if w.get("status","active")!="active":
        routes.append({"worker_id":wid,"route_status":"PAUSED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,"slot_id":None,"assignment_id":None,"work_item_id":None,
          "routing_score":None,"score_components":{},"evidence_state":PROFILES[wid].get("measured_state"),
          "claim_id":None,"reason":"Worker is paused in worker_registry.json."})
    elif wid in active_by_worker:
        s=active_by_worker[wid];a=alloc_by_slot.get(s["slot_id"]) or {}
        routes.append({"worker_id":wid,"route_status":"LOCKED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,"slot_id":s["slot_id"],
          "assignment_id":s.get("claimed_assignment_id") or a.get("assignment_id"),"work_item_id":a.get("work_item_id"),
          "routing_score":None,"score_components":{},"evidence_state":"LOCKED_ACTIVE_CLAIM",
          "claim_id":s.get("claim_id"),"reason":"Existing V11 active claim is authoritative and preserved."})
    elif wid in pair_map:
        slot=pair_map[wid];e=edge_map[(wid,slot)]
        routes.append({"worker_id":wid,"route_status":"ROUTED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,"slot_id":slot,"assignment_id":e["assignment_id"],
          "work_item_id":e["work_item_id"],"routing_score":e["routing_score"],
          "score_components":e["score_components"],"routing_learning_evidence_count":e.get("routing_learning_evidence_count",0),"evidence_state":PROFILES[wid].get("measured_state"),
          "claim_id":None,"reason":"Maximum-total-fit exact assignment across currently idle registered workers and claimable slots."})
    else:
        routes.append({"worker_id":wid,"route_status":"IDLE_UNASSIGNED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,"slot_id":None,"assignment_id":None,"work_item_id":None,
          "routing_score":None,"score_components":{},"evidence_state":PROFILES[wid].get("measured_state"),
          "claim_id":None,"reason":"No claimable slot remained after exact matching."})

(INTEL/"routing_candidates.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in edges)+("\n" if edges else ""),encoding="utf-8")
(INTEL/"worker_routing.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in routes)+"\n",encoding="utf-8")

packets=[]
for r in routes:
    if r["route_status"]!="ROUTED": continue
    a=alloc_by_slot[r["slot_id"]]
    packets.append({
      "worker_id":r["worker_id"],"routing_generation_id":routing_generation,
      "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,"slot_id":r["slot_id"],
      "assignment_id":a["assignment_id"],"allocator_generation_id":a["allocator_generation_id"],
      "portfolio_policy_generation_id":a["portfolio_policy_generation_id"],"work_item_id":a["work_item_id"],
      "assignment_slot_role":a["slot_role"],"assignment_work_kind":a["work_kind"],
      "assignment_source_id":a["source_id"],"assignment_score":a["final_score"],
      "routing_score":r["routing_score"],"routing_learning_adjustment":(r.get("score_components") or {}).get("routing_learning",0),
      "activation_response_adjustment":(r.get("score_components") or {}).get("activation_response",0),
      "routing_learning_evidence_count":r.get("routing_learning_evidence_count",0),"claim_file":f"intelligence/execution_events/{r['slot_id']}.jsonl"
    })
(INTEL/"worker_claim_packets.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in packets)+("\n" if packets else ""),encoding="utf-8")

metrics={
  "schema_version":1,"routing_generation_id":routing_generation,"worker_profile_generation_id":profile_generation,
  "routing_learning_generation_id":LEARN_GEN,"routing_learning_mode":LEARN_MET.get("mode") or "unavailable",
  "activation_response_learning_generation_id":RESPONSE_GEN,"activation_response_learning_mode":RESPONSE_MET.get("mode") or "unavailable",
  "registered_workers":len(workers),"active_locked_workers":len(active_by_worker),
  "routed_workers":sum(1 for r in routes if r["route_status"]=="ROUTED"),
  "unassigned_workers":sum(1 for r in routes if r["route_status"]=="IDLE_UNASSIGNED"),
  "claimable_slots":len(available_slots),"routed_slots":len(used_slots),"candidate_edges":len(edges)
}
(INTEL/"routing_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# WORKER ROUTING PLAN","",f"Routing generation: **{routing_generation}**",f"Worker profiles: **{profile_generation}**","",
"V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.","",
f"Routing learning: **{LEARN_GEN}** / mode **{LEARN_MET.get('mode') or 'unavailable'}**",
f"Activation-response learning: **{RESPONSE_GEN}** / mode **{RESPONSE_MET.get('mode') or 'unavailable'}**","",
"| Worker | Profile | Route | Slot | Assignment | Score | Reason |",
"|---|---|---|---|---|---:|---|"]
for r in routes:
    score_text="—" if r.get("routing_score") is None else f"{r['routing_score']:.2f}"
    report.append(f"| {r['worker_id']} | {r['evidence_state']} | {r['route_status']} | {r.get('slot_id') or '—'} | {r.get('assignment_id') or '—'} | {score_text} | {r['reason']} |")
report += ["","## Routing interpretation","",
"- Assignment priority is preserved in every worker-slot score.",
"- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.",
"- Unmeasured workers get an exploration bonus; they are not treated as low quality.",
"- Current active claims are locked and consume worker capacity.",
"- V13 learned task-context adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.",
"- V17 activation-response adjustment is penalty-only and stays zero until READY→activation→claim evidence thresholds are satisfied.",
"- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.",""]
(INTEL/"WORKER_ROUTING.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
