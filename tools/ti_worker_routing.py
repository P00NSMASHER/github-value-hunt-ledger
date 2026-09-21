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
EXP_POL=json.loads((INTEL/"routing_exploration_policy.json").read_text(encoding="utf-8")) if (INTEL/"routing_exploration_policy.json").exists() else {}
EXP_HISTORY=load_jsonl("routing_exploration_history.jsonl") if (INTEL/"routing_exploration_history.jsonl").exists() else []
ROUTE_RUNS=load_jsonl("routing_learning_runs.jsonl") if (INTEL/"routing_learning_runs.jsonl").exists() else []
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
baseline_pairs=list(pairs)

def pair_score(pairs):
    total=0.0
    for wid,slot in pairs:
        e=edge_map.get((wid,slot))
        if not e:
            return None
        total+=float(e["routing_score"])
    return round(total,6)

def match_info(a,b):
    if a.get("slot_role")!=b.get("slot_role") or a.get("work_kind")!=b.get("work_kind"):
        return 0,None
    same_strategy=bool(a.get("strategy_id")) and a.get("strategy_id")==b.get("strategy_id")
    same_objective=bool(a.get("search_objective_id")) and a.get("search_objective_id")==b.get("search_objective_id")
    if same_strategy and same_objective:
        return 3,"role+work_kind+strategy+objective"
    if same_strategy:
        return 2,"role+work_kind+strategy"
    if same_objective:
        return 2,"role+work_kind+objective"
    return 1,"role+work_kind"

generated_route_counts={}
for rr in ROUTE_RUNS:
    wid=rr.get("worker_id")
    if wid:
        generated_route_counts[wid]=generated_route_counts.get(wid,0)+1

def controlled_exploration_decision(baseline):
    baseline_total=pair_score(baseline)
    base_payload={
      "profile_generation":P_MET.get("worker_profile_generation_id"),
      "routing_learning_generation":LEARN_GEN,
      "activation_response_learning_generation":RESPONSE_GEN,
      "state":[(x.get("slot_id"),x.get("status"),x.get("worker_id"),x.get("current_assignment_id")) for x in STATE],
      "alloc":[(x["slot_id"],x["assignment_id"],x.get("final_score")) for x in ALLOC],
      "baseline_routes":sorted(baseline)
    }
    seed_raw=json.dumps(base_payload,sort_keys=True,separators=(",",":"))
    seed_hash=hashlib.sha256(seed_raw.encode()).hexdigest()
    exp_gen="ROUTEEXP:"+seed_hash[:12]
    gate=int(seed_hash[12:20],16)/float(0xFFFFFFFF)
    probability=float(EXP_POL.get("exploration_probability",0.25))
    min_level=int(EXP_POL.get("min_match_level",2))
    max_abs=float(EXP_POL.get("max_absolute_regret",1.5))
    max_rel=float(EXP_POL.get("max_relative_regret",0.05))
    target_routes=int(EXP_POL.get("target_completed_generated_routes_per_worker",3))
    eligible_roles=set(EXP_POL.get("eligible_slot_roles") or ["experiment","coverage","adjacency"])
    decision={
      "exploration_generation_id":exp_gen,
      "seed_hash":seed_hash,
      "gate_value":round(gate,8),
      "exploration_probability":probability,
      "baseline_total_score":baseline_total,
      "applied":False,
      "reason":"gate_closed" if gate>=probability else "no_eligible_low_regret_swap",
      "pair_id":None,
      "workers":[],
      "baseline_slots":[],
      "exploration_slots":[],
      "match_level":None,
      "match_basis":None,
      "absolute_regret":0.0,
      "relative_regret":0.0,
      "measurement_need":0,
      "candidate_count":0
    }
    if not EXP_POL or not EXP_POL.get("enabled",True):
        decision["reason"]="disabled"
        return baseline,decision
    if gate>=probability:
        return baseline,decision
    candidates=[]
    pairs_sorted=sorted(baseline)
    for i in range(len(pairs_sorted)):
        w1,s1=pairs_sorted[i]; a1=alloc_by_slot[s1]
        if a1.get("slot_role") not in eligible_roles:
            continue
        for j in range(i+1,len(pairs_sorted)):
            w2,s2=pairs_sorted[j]; a2=alloc_by_slot[s2]
            if a2.get("slot_role") not in eligible_roles:
                continue
            level,basis=match_info(a1,a2)
            if level<min_level:
                continue
            e11=edge_map.get((w1,s1)); e22=edge_map.get((w2,s2))
            e12=edge_map.get((w1,s2)); e21=edge_map.get((w2,s1))
            if not all([e11,e22,e12,e21]):
                continue
            base=float(e11["routing_score"])+float(e22["routing_score"])
            alt=float(e12["routing_score"])+float(e21["routing_score"])
            regret=max(0.0,base-alt)
            rel=regret/max(abs(base),1e-9)
            if regret>max_abs+1e-12 or rel>max_rel+1e-12:
                continue
            need=max(0,target_routes-generated_route_counts.get(w1,0))+max(0,target_routes-generated_route_counts.get(w2,0))
            if need<=0:
                continue
            key_raw=f"{exp_gen}|{w1}|{s1}|{w2}|{s2}"
            key_hash=hashlib.sha256(key_raw.encode()).hexdigest()
            candidates.append({
              "w1":w1,"s1":s1,"w2":w2,"s2":s2,
              "match_level":level,"match_basis":basis,
              "base_score":round(base,6),"alt_score":round(alt,6),
              "absolute_regret":round(regret,6),"relative_regret":round(rel,6),
              "measurement_need":need,"selection_hash":key_hash
            })
    decision["candidate_count"]=len(candidates)
    if not candidates:
        return baseline,decision
    max_level=max(x["match_level"] for x in candidates)
    candidates=[x for x in candidates if x["match_level"]==max_level]
    max_need=max(x["measurement_need"] for x in candidates)
    candidates=[x for x in candidates if x["measurement_need"]==max_need]
    candidates.sort(key=lambda x:(x["selection_hash"],x["w1"],x["w2"],x["s1"],x["s2"]))
    chosen=candidates[0]
    swapped=[]
    for wid,slot in baseline:
        if wid==chosen["w1"]:
            swapped.append((wid,chosen["s2"]))
        elif wid==chosen["w2"]:
            swapped.append((wid,chosen["s1"]))
        else:
            swapped.append((wid,slot))
    pair_id="EXPPAIR:"+hashlib.sha256(
      f"{exp_gen}|{chosen['w1']}|{chosen['s1']}|{chosen['w2']}|{chosen['s2']}".encode()
    ).hexdigest()[:12]
    decision.update({
      "applied":True,
      "reason":"controlled_low_regret_swap",
      "pair_id":pair_id,
      "workers":[chosen["w1"],chosen["w2"]],
      "baseline_slots":[chosen["s1"],chosen["s2"]],
      "exploration_slots":[chosen["s2"],chosen["s1"]],
      "match_level":chosen["match_level"],
      "match_basis":chosen["match_basis"],
      "absolute_regret":chosen["absolute_regret"],
      "relative_regret":chosen["relative_regret"],
      "measurement_need":chosen["measurement_need"]
    })
    return swapped,decision

pairs,controlled_exploration_decision=controlled_exploration_decision(baseline_pairs)
pair_map={wid:slot for wid,slot in pairs}
baseline_pair_map={wid:slot for wid,slot in baseline_pairs}
used_slots=set(pair_map.values())

fingerprint=json.dumps({
  "profile_generation":P_MET.get("worker_profile_generation_id"),
  "routing_learning_generation":LEARN_GEN,
  "activation_response_learning_generation":RESPONSE_GEN,
  "routing_exploration_generation":controlled_exploration_decision["exploration_generation_id"],
  "routing_exploration_pair":controlled_exploration_decision.get("pair_id"),
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
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,
          "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],"routing_exploration_pair_id":None,
          "baseline_slot_id":None,"route_mode":"paused","slot_id":None,"assignment_id":None,"work_item_id":None,
          "routing_score":None,"score_components":{},"evidence_state":PROFILES[wid].get("measured_state"),
          "claim_id":None,"reason":"Worker is paused in worker_registry.json."})
    elif wid in active_by_worker:
        s=active_by_worker[wid];a=alloc_by_slot.get(s["slot_id"]) or {}
        routes.append({"worker_id":wid,"route_status":"LOCKED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,
          "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],"routing_exploration_pair_id":None,
          "baseline_slot_id":s["slot_id"],"route_mode":"locked","slot_id":s["slot_id"],
          "assignment_id":s.get("claimed_assignment_id") or a.get("assignment_id"),"work_item_id":a.get("work_item_id"),
          "routing_score":None,"score_components":{},"evidence_state":"LOCKED_ACTIVE_CLAIM",
          "claim_id":s.get("claim_id"),"reason":"Existing V11 active claim is authoritative and preserved."})
    elif wid in pair_map:
        slot=pair_map[wid];e=edge_map[(wid,slot)]
        routes.append({"worker_id":wid,"route_status":"ROUTED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,
          "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],
          "routing_exploration_pair_id":controlled_exploration_decision.get("pair_id") if wid in set(controlled_exploration_decision.get("workers") or []) else None,
          "baseline_slot_id":baseline_pair_map.get(wid),
          "route_mode":"explore_swap" if controlled_exploration_decision.get("applied") and wid in set(controlled_exploration_decision.get("workers") or []) else "exploit",
          "slot_id":slot,"assignment_id":e["assignment_id"],
          "work_item_id":e["work_item_id"],"routing_score":e["routing_score"],
          "score_components":e["score_components"],"routing_learning_evidence_count":e.get("routing_learning_evidence_count",0),"evidence_state":PROFILES[wid].get("measured_state"),
          "claim_id":None,"reason":"Maximum-total-fit exact assignment across currently idle registered workers and claimable slots."})
    else:
        routes.append({"worker_id":wid,"route_status":"IDLE_UNASSIGNED","routing_generation_id":routing_generation,
          "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,
          "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],"routing_exploration_pair_id":None,
          "baseline_slot_id":None,"route_mode":"unassigned","slot_id":None,"assignment_id":None,"work_item_id":None,
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
      "worker_profile_generation_id":profile_generation,"routing_learning_generation_id":LEARN_GEN,"activation_response_learning_generation_id":RESPONSE_GEN,
      "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],"routing_exploration_pair_id":r.get("routing_exploration_pair_id"),
      "baseline_slot_id":r.get("baseline_slot_id"),"route_mode":r.get("route_mode"),"slot_id":r["slot_id"],
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
  "routing_exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],
  "routing_exploration_applied":bool(controlled_exploration_decision.get("applied")),
  "routing_exploration_pair_id":controlled_exploration_decision.get("pair_id"),
  "routing_exploration_absolute_regret":controlled_exploration_decision.get("absolute_regret",0.0),
  "registered_workers":len(workers),"active_locked_workers":len(active_by_worker),
  "routed_workers":sum(1 for r in routes if r["route_status"]=="ROUTED"),
  "unassigned_workers":sum(1 for r in routes if r["route_status"]=="IDLE_UNASSIGNED"),
  "claimable_slots":len(available_slots),"routed_slots":len(used_slots),"candidate_edges":len(edges)
}
(INTEL/"routing_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
controlled_exploration_decision["routing_generation_id"]=routing_generation
controlled_exploration_decision["worker_profile_generation_id"]=profile_generation
controlled_exploration_decision["routing_learning_generation_id"]=LEARN_GEN
controlled_exploration_decision["activation_response_learning_generation_id"]=RESPONSE_GEN
(INTEL/"routing_exploration_decision.json").write_text(json.dumps(controlled_exploration_decision,indent=2)+"\n",encoding="utf-8")
history_by_gen={x.get("exploration_generation_id"):x for x in EXP_HISTORY if x.get("exploration_generation_id")}
old=history_by_gen.get(controlled_exploration_decision["exploration_generation_id"])
if old:
    immutable=["seed_hash","gate_value","exploration_probability","applied","reason","pair_id","workers","baseline_slots","exploration_slots","match_level","match_basis","absolute_regret","relative_regret","measurement_need","candidate_count"]
    drift=[k for k in immutable if old.get(k)!=controlled_exploration_decision.get(k)]
    if drift:
        raise SystemExit(f"routing exploration history drift: {','.join(drift)}")
else:
    history_by_gen[controlled_exploration_decision["exploration_generation_id"]]=controlled_exploration_decision
exp_history=sorted(history_by_gen.values(),key=lambda x:x["exploration_generation_id"])
(INTEL/"routing_exploration_history.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in exp_history)+("\n" if exp_history else ""),encoding="utf-8")
exp_metrics={
  "schema_version":1,
  "exploration_generation_id":controlled_exploration_decision["exploration_generation_id"],
  "routing_generation_id":routing_generation,
  "applied":bool(controlled_exploration_decision.get("applied")),
  "pair_id":controlled_exploration_decision.get("pair_id"),
  "candidate_count":controlled_exploration_decision.get("candidate_count",0),
  "absolute_regret":controlled_exploration_decision.get("absolute_regret",0.0),
  "relative_regret":controlled_exploration_decision.get("relative_regret",0.0),
  "history_generations":len(exp_history),
  "history_applied_swaps":sum(1 for x in exp_history if x.get("applied"))
}
(INTEL/"routing_exploration_metrics.json").write_text(json.dumps(exp_metrics,indent=2)+"\n",encoding="utf-8")
exp_report=[
  "# CONTROLLED ROUTING EXPLORATION","",
  f"Generation: **{controlled_exploration_decision['exploration_generation_id']}**",
  f"Routing generation: **{routing_generation}**",
  f"Gate: **{controlled_exploration_decision['gate_value']:.4f} / {controlled_exploration_decision['exploration_probability']:.4f}**",
  f"Applied: **{controlled_exploration_decision['applied']}**",
  f"Reason: **{controlled_exploration_decision['reason']}**","",
  "V18 may alter at most one two-worker pairing per routing generation. It never changes the assignment portfolio itself.",""
]
if controlled_exploration_decision.get("applied"):
    exp_report += [
      f"- Pair: **{controlled_exploration_decision['pair_id']}**",
      f"- Workers: **{', '.join(controlled_exploration_decision['workers'])}**",
      f"- Baseline slots: **{', '.join(controlled_exploration_decision['baseline_slots'])}**",
      f"- Exploration slots: **{', '.join(controlled_exploration_decision['exploration_slots'])}**",
      f"- Match basis: **{controlled_exploration_decision['match_basis']}**",
      f"- Absolute routing-score regret: **{controlled_exploration_decision['absolute_regret']:.4f}**",
      f"- Relative regret: **{100*controlled_exploration_decision['relative_regret']:.2f}%**",
      f"- Measurement need: **{controlled_exploration_decision['measurement_need']}**"
    ]
else:
    exp_report += ["- Baseline maximum-total-fit routing is unchanged."]
exp_report += ["",
  "Exploration is deterministic from pre-outcome routing state and is designed to create low-regret assignment variation for later matched analysis. It is not evidence that one worker is better than another.",""]
(INTEL/"ROUTING_EXPLORATION.md").write_text("\n".join(exp_report),encoding="utf-8")

report=["# WORKER ROUTING PLAN","",f"Routing generation: **{routing_generation}**",f"Worker profiles: **{profile_generation}**","",
"V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.","",
f"Routing learning: **{LEARN_GEN}** / mode **{LEARN_MET.get('mode') or 'unavailable'}**",
f"Activation-response learning: **{RESPONSE_GEN}** / mode **{RESPONSE_MET.get('mode') or 'unavailable'}**",
f"Routing exploration: **{controlled_exploration_decision['exploration_generation_id']}** / applied **{controlled_exploration_decision['applied']}**","",
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
"- V18 may apply at most one deterministic low-regret matched worker swap to create controlled assignment variation.",
"- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.",""]
(INTEL/"WORKER_ROUTING.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
