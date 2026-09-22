#!/usr/bin/env python3
import json,re
from ti_common import INTEL, ROOT, load_jsonl

from ti_learning_measurement_blinding import (
    worker_measurement_blinding_errors,
)
from ti_search_actions import action_errors, capability_recipe

seeds=load_jsonl("search_seeds.jsonl")
caps={x["capability_id"] for x in load_jsonl("capabilities.jsonl")}
strats={x["strategy_id"] for x in load_jsonl("search_strategies.jsonl")}
obj=json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8"))
objs={x["search_objective_id"] for x in obj.get("objectives",[])}
runs=load_jsonl("search_runs.jsonl")
coverage_gap_ids_active={x["coverage_gap_id"] for x in load_jsonl("exploration_gap_queue.jsonl")} if (INTEL/"exploration_gap_queue.jsonl").exists() else set()
learning_curriculum=json.loads((INTEL/"learning_curriculum.json").read_text(encoding="utf-8")) if (INTEL/"learning_curriculum.json").exists() else {}
learning_recommendations={
    row.get("strategy_id"): row
    for row in learning_curriculum.get("recommended_measurements") or []
    if isinstance(row,dict)
    and isinstance(row.get("strategy_id"),str)
}
seen=set()
for n,s in enumerate(seeds,1):
    sid=s.get("seed_id")
    if not sid or not re.match(r"^SEED:[a-z0-9:-]+$",sid):
        raise SystemExit(f"search_seeds.jsonl:{n}: invalid seed_id {sid}")
    if sid in seen:
        raise SystemExit(f"search_seeds.jsonl:{n}: duplicate seed_id {sid}")
    seen.add(sid)
    if s.get("seed_type") not in {"capability_gap","positive_dna_transfer","learning_measurement","coverage_gap"}:
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
    if s.get("work_action","search")=="search" and not s.get("query_templates"):
        raise SystemExit(f"search_seeds.jsonl:{n}: no query templates")
    errors=action_errors(s)
    if errors: raise SystemExit(f"search_seeds.jsonl:{n}: {'; '.join(errors)}")
    if s.get("seed_type")=="capability_gap" and "work_action" in s:
        for cid in s.get("capability_ids") or []:
            if s["work_action"]!=capability_recipe(cid)["work_action"]:
                raise SystemExit(f"search_seeds.jsonl:{n}: action differs from reviewed capability recipe")
    if s.get("seed_type") in {"coverage_gap","learning_measurement"} and "work_action" in s:
        parent=next((x for x in seeds if x["seed_id"]==s.get("parent_seed_id")),None)
        if not parent or parent.get("work_action")!="search" or s["work_action"]!="search":
            raise SystemExit(f"search_seeds.jsonl:{n}: derived discovery must inherit an authorized search parent")
        if not set(parent.get("stop_conditions",[])).issubset(s.get("stop_conditions",[])):
            raise SystemExit(f"search_seeds.jsonl:{n}: derived seed dropped parent STOP gates")
    if s.get("seed_type")=="learning_measurement":
        rec=learning_recommendations.get(s.get("strategy_id"))
        if not rec:
            raise SystemExit(f"search_seeds.jsonl:{n}: learning measurement is not a current curriculum recommendation")
        blind_errors=worker_measurement_blinding_errors(s)
        if blind_errors:
            raise SystemExit(
                f"search_seeds.jsonl:{n}: worker measurement blinding failed: "
                + "; ".join(blind_errors)
            )
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
            if not re.match(r"^SEED:[a-z0-9:-]+$",sid):
                raise SystemExit(f"search_runs.jsonl:{n}: invalid historical seed_id {sid}")
print(f"OK seeds={len(seeds)} v5_runs={sum(1 for r in runs if (r.get('schema_version') or 0)>=5)}")
