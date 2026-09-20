#!/usr/bin/env python3
import json,re
from ti_common import INTEL, load_jsonl

seeds=load_jsonl("search_seeds.jsonl")
caps={x["capability_id"] for x in load_jsonl("capabilities.jsonl")}
strats={x["strategy_id"] for x in load_jsonl("search_strategies.jsonl")}
obj=json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8"))
objs={x["search_objective_id"] for x in obj.get("objectives",[])}
runs=load_jsonl("search_runs.jsonl")
coverage_gap_ids_active={x["coverage_gap_id"] for x in load_jsonl("exploration_gap_queue.jsonl")} if (INTEL/"exploration_gap_queue.jsonl").exists() else set()
seen=set()
for n,s in enumerate(seeds,1):
    sid=s.get("seed_id")
    if not sid or not re.match(r"^SEED:[a-z0-9:-]+$",sid):
        raise SystemExit(f"search_seeds.jsonl:{n}: invalid seed_id {sid}")
    if sid in seen:
        raise SystemExit(f"search_seeds.jsonl:{n}: duplicate seed_id {sid}")
    seen.add(sid)
    if s.get("seed_type") not in {"capability_gap","positive_dna_transfer","strategy_measurement","coverage_gap"}:
        raise SystemExit(f"search_seeds.jsonl:{n}: invalid seed_type")
    p=s.get("priority")
    if not isinstance(p,(int,float)) or not (0<=p<=100):
        raise SystemExit(f"search_seeds.jsonl:{n}: priority out of range")
    if s.get("strategy_id") not in strats:
        raise SystemExit(f"search_seeds.jsonl:{n}: unknown strategy {s.get('strategy_id')}")
    if s.get("search_objective_id") not in objs:
        raise SystemExit(f"search_seeds.jsonl:{n}: unknown objective {s.get('search_objective_id')}")
    for cid in s.get("capability_ids",[]):
        if cid not in caps:
            raise SystemExit(f"search_seeds.jsonl:{n}: unknown capability {cid}")
    if not s.get("query_templates"):
        raise SystemExit(f"search_seeds.jsonl:{n}: no query templates")
    if s.get("seed_type")=="coverage_gap":
        gids=s.get("coverage_gap_ids") or []
        if not gids: raise SystemExit(f"search_seeds.jsonl:{n}: coverage_gap seed missing coverage_gap_ids")
        for gid in gids:
            if gid not in coverage_gap_ids_active: raise SystemExit(f"search_seeds.jsonl:{n}: inactive/unknown coverage gap {gid}")
for n,r in enumerate(runs,1):
    if (r.get("schema_version") or 0)>=5:
        mode=r.get("seed_mode")
        ids=r.get("seed_ids")
        if mode not in {"generated","manual_hypothesis","free_exploration"}:
            raise SystemExit(f"search_runs.jsonl:{n}: invalid V5 seed_mode {mode}")
        if not isinstance(ids,list):
            raise SystemExit(f"search_runs.jsonl:{n}: V5 seed_ids must be list")
        if mode=="generated" and not ids:
            raise SystemExit(f"search_runs.jsonl:{n}: generated seed_mode requires seed_ids")
        if mode=="free_exploration" and ids:
            raise SystemExit(f"search_runs.jsonl:{n}: free_exploration must not claim generated seed_ids")
        for sid in ids:
            if sid not in seen:
                raise SystemExit(f"search_runs.jsonl:{n}: unknown seed_id {sid}")
print(f"OK seeds={len(seeds)} v5_runs={sum(1 for r in runs if (r.get('schema_version') or 0)>=5)}")
