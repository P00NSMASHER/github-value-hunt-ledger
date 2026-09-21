#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_exploration_policy.json").read_text(encoding="utf-8"))
DEC=json.loads((INTEL/"routing_exploration_decision.json").read_text(encoding="utf-8"))
HIST=load_jsonl("routing_exploration_history.jsonl")
ROUTES=load_jsonl("worker_routing.jsonl")
PACKETS=load_jsonl("worker_claim_packets.jsonl")
ALLOC=load_jsonl("hunt_allocations.jsonl")
MET=json.loads((INTEL/"routing_metrics.json").read_text(encoding="utf-8"))
EMET=json.loads((INTEL/"routing_exploration_metrics.json").read_text(encoding="utf-8"))

routes={x["worker_id"]:x for x in ROUTES}
packets={x["worker_id"]:x for x in PACKETS}
alloc={x["slot_id"]:x for x in ALLOC}
exp_gen=DEC.get("exploration_generation_id")
if not exp_gen or not str(exp_gen).startswith("ROUTEEXP:"):
    raise SystemExit("missing/invalid exploration generation")
if MET.get("routing_exploration_generation_id")!=exp_gen or EMET.get("exploration_generation_id")!=exp_gen:
    raise SystemExit("exploration generation drift")
if EMET.get("routing_generation_id")!=DEC.get("routing_generation_id"):
    raise SystemExit("exploration routing generation drift")

history_by={x.get("exploration_generation_id"):x for x in HIST}
if len(history_by)!=len(HIST):
    raise SystemExit("routing exploration history contains duplicate generation IDs")
if exp_gen not in history_by:
    raise SystemExit("current exploration decision missing from history")
hist=history_by[exp_gen]
immutable=[
  "seed_hash","gate_value","exploration_probability","applied","reason","pair_id",
  "workers","baseline_slots","exploration_slots","match_level","match_basis",
  "absolute_regret","relative_regret","measurement_need","candidate_count"
]
drift=[k for k in immutable if hist.get(k)!=DEC.get(k)]
if drift:
    raise SystemExit("routing exploration history drift: "+",".join(drift))

prob=float(POL.get("exploration_probability",0.25))
if abs(float(DEC.get("exploration_probability"))-prob)>1e-12:
    raise SystemExit("decision exploration probability drift")
gate=float(DEC.get("gate_value"))
if DEC.get("applied") and gate>=prob:
    raise SystemExit("exploration applied while deterministic gate was closed")
if not DEC.get("applied") and DEC.get("reason")=="gate_closed" and gate<prob:
    raise SystemExit("gate_closed reason inconsistent with gate value")

explore=[r for r in ROUTES if r.get("route_mode")=="explore_swap"]
if DEC.get("applied"):
    if int(POL.get("max_swaps_per_generation",1))!=1:
        raise SystemExit("validator currently requires max_swaps_per_generation=1")
    if len(explore)!=2:
        raise SystemExit("applied V18 decision must alter exactly two routed workers")
    if not DEC.get("pair_id") or len(DEC.get("workers") or [])!=2:
        raise SystemExit("applied decision missing pair metadata")
    if set(x["worker_id"] for x in explore)!=set(DEC["workers"]):
        raise SystemExit("exploratory route workers do not match decision")
    if set(x.get("routing_exploration_pair_id") for x in explore)!={DEC["pair_id"]}:
        raise SystemExit("exploratory routes do not carry exact pair ID")
    if len(DEC.get("baseline_slots") or [])!=2 or len(DEC.get("exploration_slots") or [])!=2:
        raise SystemExit("applied decision must contain exactly two baseline/exploration slots")
    for wid,baseline_slot,new_slot in zip(DEC["workers"],DEC["baseline_slots"],DEC["exploration_slots"]):
        r=routes.get(wid)
        if not r or r.get("baseline_slot_id")!=baseline_slot or r.get("slot_id")!=new_slot:
            raise SystemExit(f"exploration route mismatch for {wid}")
        if baseline_slot==new_slot:
            raise SystemExit(f"exploration route did not actually swap {wid}")
        p=packets.get(wid)
        if not p or p.get("route_mode")!="explore_swap" or p.get("routing_exploration_pair_id")!=DEC["pair_id"]:
            raise SystemExit(f"claim packet missing exploration provenance for {wid}")
    if int(DEC.get("match_level") or 0)<int(POL.get("min_match_level",2)):
        raise SystemExit("exploration match level below policy")
    if float(DEC.get("absolute_regret") or 0)>float(POL.get("max_absolute_regret",1.5))+1e-12:
        raise SystemExit("absolute exploration regret exceeds policy")
    if float(DEC.get("relative_regret") or 0)>float(POL.get("max_relative_regret",0.05))+1e-12:
        raise SystemExit("relative exploration regret exceeds policy")
    if int(DEC.get("measurement_need") or 0)<=0:
        raise SystemExit("exploration applied without measurement debt")
    eligible=set(POL.get("eligible_slot_roles") or [])
    for slot in DEC["baseline_slots"]:
        if alloc[slot].get("slot_role") not in eligible:
            raise SystemExit("exploration touched excluded slot role")
else:
    if explore:
        raise SystemExit("non-applied exploration decision has exploratory routes")
    if DEC.get("pair_id") is not None:
        raise SystemExit("non-applied exploration decision must not have pair_id")

for n,r in enumerate(ROUTES,1):
    if r.get("routing_exploration_generation_id")!=exp_gen:
        raise SystemExit(f"worker_routing.jsonl:{n}: exploration generation drift")
    if r.get("route_mode")=="exploit" and r.get("baseline_slot_id")!=r.get("slot_id"):
        raise SystemExit(f"worker_routing.jsonl:{n}: exploit route differs from baseline slot")
for n,p in enumerate(PACKETS,1):
    if p.get("routing_exploration_generation_id")!=exp_gen:
        raise SystemExit(f"worker_claim_packets.jsonl:{n}: exploration generation drift")
    r=routes.get(p["worker_id"])
    if not r or p.get("route_mode")!=r.get("route_mode") or p.get("baseline_slot_id")!=r.get("baseline_slot_id"):
        raise SystemExit(f"worker_claim_packets.jsonl:{n}: exploration provenance mismatch")

if bool(EMET.get("applied"))!=bool(DEC.get("applied")):
    raise SystemExit("exploration metrics applied drift")
if EMET.get("pair_id")!=DEC.get("pair_id"):
    raise SystemExit("exploration metrics pair drift")
print(f"OK exploration_generation={exp_gen} applied={DEC.get('applied')} candidates={DEC.get('candidate_count')} regret={DEC.get('absolute_regret')}")
