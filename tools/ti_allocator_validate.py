#!/usr/bin/env python3
import json,re
from collections import Counter
from ti_common import INTEL, load_jsonl

policy_path=INTEL/"allocator_policy_effective.json" if (INTEL/"allocator_policy_effective.json").exists() else INTEL/"allocator_policy.json"
cfg=json.loads(policy_path.read_text(encoding="utf-8"))
portfolio_policy_id=(cfg.get("learning") or {}).get("portfolio_policy_generation_id") or "PORTFOLIO:000000000000"
cand=load_jsonl("hunt_candidates.jsonl")
alloc=load_jsonl("hunt_allocations.jsonl")
metrics=json.loads((INTEL/"allocator_metrics.json").read_text(encoding="utf-8"))
runs=load_jsonl("search_runs.jsonl")

cids=set()
for n,c in enumerate(cand,1):
    wid=c.get("work_item_id")
    if not wid or wid in cids: raise SystemExit(f"hunt_candidates.jsonl:{n}: missing/duplicate work_item_id")
    cids.add(wid)
    if not isinstance(c.get("final_score"),(int,float)): raise SystemExit(f"hunt_candidates.jsonl:{n}: score missing")

slots={x["slot_id"]:x for x in cfg.get("slots",[])}
seen_slots=set(); seen_assign=set()
caps=Counter(); exps=Counter(); strats=Counter(); roots=Counter(); kinds=Counter(); roles=Counter()
for n,a in enumerate(alloc,1):
    aid=a.get("assignment_id")
    if not aid or aid in seen_assign: raise SystemExit(f"hunt_allocations.jsonl:{n}: missing/duplicate assignment_id")
    seen_assign.add(aid)
    sid=a.get("slot_id")
    if sid not in slots or sid in seen_slots: raise SystemExit(f"hunt_allocations.jsonl:{n}: invalid/duplicate slot {sid}")
    seen_slots.add(sid)
    if a.get("work_item_id") not in cids: raise SystemExit(f"hunt_allocations.jsonl:{n}: unknown work item")
    if a.get("portfolio_policy_generation_id")!=portfolio_policy_id: raise SystemExit(f"hunt_allocations.jsonl:{n}: assignment portfolio policy mismatch")
    kinds[a.get("work_kind")]+=1
    roles[a.get("slot_role")]+=1
    for cid in a.get("capability_ids") or []: caps[cid]+=1
    for eid in a.get("experiment_ids") or []: exps[eid]+=1
    if a.get("strategy_id"): strats[a["strategy_id"]]+=1
    if a.get("adjacency_root"): roots[a["adjacency_root"]]+=1

cons=cfg["constraints"]
if len(alloc)!=cfg["slot_count"] or len(seen_slots)!=cfg["slot_count"]: raise SystemExit("allocator did not fill every slot exactly once")
if caps and max(caps.values())>cons["max_assignments_per_capability"]: raise SystemExit("capability concentration exceeded")
if exps and max(exps.values())>cons["max_assignments_per_experiment"]: raise SystemExit("experiment concentration exceeded")
if strats and max(strats.values())>cons["max_assignments_per_strategy"]: raise SystemExit("strategy concentration exceeded")
if roots and max(roots.values())>cons["max_adjacency_assignments_per_root"]: raise SystemExit("adjacency root concentration exceeded")
if roles["coverage"]<cons["min_coverage_role_slots"]: raise SystemExit("coverage role reserve not met")
if kinds["coverage_gap"]<cons["min_coverage_gap_assignments"]: raise SystemExit("coverage-gap assignment reserve not met")
if kinds["adjacency"]<cons["min_adjacency_slots"]: raise SystemExit("adjacency reserve not met")
if kinds["strategy_measurement"]<cons["min_measurement_slots"]: raise SystemExit("measurement reserve not met")
if kinds["independent_verification"]<cons["min_verification_slots"]: raise SystemExit("verification reserve not met")
if kinds["wildcard"]<cons["min_wildcard_slots"]: raise SystemExit("wildcard reserve not met")
if metrics.get("assignment_count")!=len(alloc): raise SystemExit("allocator_metrics assignment count drift")
if metrics.get("portfolio_policy_generation_id")!=portfolio_policy_id: raise SystemExit("allocator_metrics portfolio policy mismatch")

for n,r in enumerate(runs,1):
    if (r.get("schema_version") or 0)<9: continue
    mode=r.get("allocation_mode")
    if mode not in {"generated","manual_override","unallocated"}: raise SystemExit(f"search_runs.jsonl:{n}: invalid V9 allocation_mode")
    if mode=="generated":
        if not r.get("allocator_generation_id") or not r.get("assignment_id") or not r.get("assignment_work_item_id"):
            raise SystemExit(f"search_runs.jsonl:{n}: generated V9 run missing allocator provenance")
    if mode=="unallocated" and (r.get("assignment_id") or r.get("assignment_work_item_id")):
        raise SystemExit(f"search_runs.jsonl:{n}: unallocated run claims assignment")
print(f"OK candidates={len(cand)} assignments={len(alloc)} generation={metrics.get('allocator_generation_id')}")
