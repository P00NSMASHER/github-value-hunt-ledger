#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl

REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
POL=json.loads((INTEL/"routing_policy.json").read_text(encoding="utf-8"))
LEARN_POL=json.loads((INTEL/"routing_learning_policy.json").read_text(encoding="utf-8"))
LEARN_MET=json.loads((INTEL/"routing_learning_metrics.json").read_text(encoding="utf-8"))
RESP_POL=json.loads((INTEL/"activation_response_policy.json").read_text(encoding="utf-8")) if (INTEL/"activation_response_policy.json").exists() else {}
RESP_MET=json.loads((INTEL/"activation_response_metrics.json").read_text(encoding="utf-8")) if (INTEL/"activation_response_metrics.json").exists() else {}
RESP_ADJ=load_jsonl("activation_response_adjustments.jsonl") if (INTEL/"activation_response_adjustments.jsonl").exists() else []
EXP_MET=json.loads((INTEL/"routing_exploration_metrics.json").read_text(encoding="utf-8")) if (INTEL/"routing_exploration_metrics.json").exists() else {}
workers={w["worker_id"]:w for w in REG["workers"]}
profiles=load_jsonl("worker_profiles.jsonl")
routes=load_jsonl("worker_routing.jsonl")
packets=load_jsonl("worker_claim_packets.jsonl")
state=load_jsonl("execution_state.jsonl")
alloc=load_jsonl("hunt_allocations.jsonl")
runs=load_jsonl("search_runs.jsonl")
metrics=json.loads((INTEL/"routing_metrics.json").read_text(encoding="utf-8"))

if len(workers)!=14: raise SystemExit("worker registry must contain exactly 14 workers")
if set(x["worker_id"] for x in profiles)!=set(workers): raise SystemExit("worker profile coverage drift")
if set(x["worker_id"] for x in routes)!=set(workers): raise SystemExit("worker routing coverage drift")
if len({x["worker_id"] for x in routes})!=len(routes): raise SystemExit("duplicate worker route")

state_by_slot={x["slot_id"]:x for x in state}
alloc_by_slot={x["slot_id"]:x for x in alloc}
used_slots=[]
route_by_worker={x["worker_id"]:x for x in routes}
for r in routes:
    if r["route_status"] in {"ROUTED","LOCKED"}:
        if not r.get("slot_id") or r["slot_id"] not in state_by_slot: raise SystemExit(f"route {r['worker_id']} missing/unknown slot")
        used_slots.append(r["slot_id"])
    if r["route_status"]=="LOCKED":
        s=state_by_slot[r["slot_id"]]
        if s.get("worker_id")!=r["worker_id"] or s.get("status") not in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}:
            raise SystemExit(f"locked route does not match active V11 claim for {r['worker_id']}")
    if r["route_status"]=="ROUTED":
        s=state_by_slot[r["slot_id"]]
        if s.get("status") not in set(POL.get("allowed_claimable_states") or []):
            raise SystemExit(f"generated route targets non-claimable slot {r['slot_id']}")
        a=alloc_by_slot[r["slot_id"]]
        if r.get("assignment_id")!=a.get("assignment_id") or r.get("work_item_id")!=a.get("work_item_id"):
            raise SystemExit(f"generated route assignment drift for {r['worker_id']}")
if len(used_slots)!=len(set(used_slots)): raise SystemExit("multiple workers routed to same slot")

active_workers={s.get("worker_id") for s in state if s.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"} and s.get("worker_id")}
for w in active_workers:
    if route_by_worker[w]["route_status"]!="LOCKED": raise SystemExit(f"active worker {w} not locked")

learn_gen=LEARN_MET.get("routing_learning_generation_id")
if not learn_gen: raise SystemExit("routing learning generation missing")
resp_gen=RESP_MET.get("response_learning_generation_id") or "RESPLEARN:000000000000"
exp_gen=EXP_MET.get("exploration_generation_id") or "ROUTEEXP:000000000000"

packet_by_worker={p["worker_id"]:p for p in packets}
for r in routes:
    if r["route_status"]=="ROUTED":
        p=packet_by_worker.get(r["worker_id"])
        if not p: raise SystemExit(f"routed worker {r['worker_id']} missing claim packet")
        if p["slot_id"]!=r["slot_id"] or p["assignment_id"]!=r["assignment_id"]:
            raise SystemExit(f"claim packet mismatch for {r['worker_id']}")
        a=alloc_by_slot[r["slot_id"]]
        if a.get("work_kind")=="learning_measurement":
            for key in ("learning_measurement_packet_id","learning_measurement_packet_sha256"):
                if not a.get(key) or p.get(key)!=a.get(key):
                    raise SystemExit(f"learning measurement packet binding drift for {r['worker_id']}: {key}")
        if p.get("routing_learning_generation_id")!=learn_gen:
            raise SystemExit(f"claim packet learning-generation mismatch for {r['worker_id']}")
        if p.get("activation_response_learning_generation_id")!=resp_gen:
            raise SystemExit(f"claim packet activation-response generation mismatch for {r['worker_id']}")
        if p.get("routing_exploration_generation_id")!=exp_gen:
            raise SystemExit(f"claim packet routing-exploration generation mismatch for {r['worker_id']}")
    elif r["worker_id"] in packet_by_worker:
        raise SystemExit(f"non-routed worker {r['worker_id']} has claim packet")

routing_ids={r["routing_generation_id"] for r in routes}
profile_ids={r["worker_profile_generation_id"] for r in routes}
if len(routing_ids)!=1 or len(profile_ids)!=1: raise SystemExit("routing/profile generation drift")
if metrics.get("routing_generation_id")!=next(iter(routing_ids)): raise SystemExit("routing metrics generation mismatch")
if metrics.get("routing_learning_generation_id")!=learn_gen: raise SystemExit("routing metrics learning-generation mismatch")
if metrics.get("activation_response_learning_generation_id")!=resp_gen: raise SystemExit("routing metrics activation-response generation mismatch")
if metrics.get("routing_exploration_generation_id")!=exp_gen: raise SystemExit("routing metrics exploration-generation mismatch")
max_pos=float(LEARN_POL.get("max_positive_adjustment",3.0))
max_neg=float(LEARN_POL.get("max_negative_adjustment",2.0))
max_resp_neg=float(RESP_POL.get("max_negative_routing_adjustment",1.0))
for n,r in enumerate(routes,1):
    if r.get("routing_learning_generation_id")!=learn_gen: raise SystemExit(f"worker_routing.jsonl:{n}: learning-generation drift")
    learned=float((r.get("score_components") or {}).get("routing_learning") or 0)
    if learned>max_pos+1e-9 or learned<-max_neg-1e-9: raise SystemExit(f"worker_routing.jsonl:{n}: learned adjustment out of bounds")
    if LEARN_MET.get("mode")!="adaptive" and abs(learned)>1e-9: raise SystemExit(f"worker_routing.jsonl:{n}: nonzero learned adjustment in observe-only mode")
    response=float((r.get("score_components") or {}).get("activation_response") or 0)
    if response>1e-9 or response < -max_resp_neg-1e-9:
        raise SystemExit(f"worker_routing.jsonl:{n}: activation-response adjustment out of bounds")
    if RESP_MET.get("mode")!="measured_feedback" and abs(response)>1e-9:
        raise SystemExit(f"worker_routing.jsonl:{n}: nonzero activation-response adjustment before V17 feedback mode")
    if r.get("activation_response_learning_generation_id")!=resp_gen:
        raise SystemExit(f"worker_routing.jsonl:{n}: activation-response generation drift")
    if r.get("routing_exploration_generation_id")!=exp_gen:
        raise SystemExit(f"worker_routing.jsonl:{n}: routing-exploration generation drift")
    if r.get("route_status")=="ROUTED" and r.get("route_mode") not in {"exploit","explore_swap"}:
        raise SystemExit(f"worker_routing.jsonl:{n}: invalid V18 route_mode")
    if r.get("route_mode")=="exploit" and r.get("baseline_slot_id")!=r.get("slot_id"):
        raise SystemExit(f"worker_routing.jsonl:{n}: exploit route differs from baseline slot")

registered=set(workers)
for n,r in enumerate(runs,1):
    if int(r.get("schema_version") or 0)<12: continue
    wid=r.get("execution_worker_id")
    if wid not in registered: raise SystemExit(f"search_runs.jsonl:{n}: unregistered execution_worker_id {wid}")
    mode=r.get("routing_mode")
    if mode not in {"generated","manual_override","unrouted"}: raise SystemExit(f"search_runs.jsonl:{n}: invalid routing_mode")
    if mode=="generated":
        required=["routing_generation_id","worker_profile_generation_id","routing_score"]
        missing=[k for k in required if r.get(k) in {None,""}]
        if missing: raise SystemExit(f"search_runs.jsonl:{n}: generated V12 route missing {','.join(missing)}")

print(f"OK workers={len(workers)} routed={metrics.get('routed_workers')} locked={metrics.get('active_locked_workers')} edges={metrics.get('candidate_edges')}")
