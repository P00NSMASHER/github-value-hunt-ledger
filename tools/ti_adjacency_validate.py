#!/usr/bin/env python3
import json,re
from ti_common import INTEL, load_jsonl

rows=load_jsonl("adjacency_queue.jsonl")
runs=load_jsonl("search_runs.jsonl")
strats={x["strategy_id"] for x in load_jsonl("search_strategies.jsonl")}
objs={x["search_objective_id"] for x in json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8")).get("objectives",[])}
allowed={"organization_siblings","contributor_lineage","fork_descendants","dependency_upstream","consumer_downstream","distinctive_symbol","commit_lineage"}
ids=set()
for n,x in enumerate(rows,1):
    aid=x.get("adjacency_id")
    if not aid or not re.match(r"^ADJ:[a-z0-9-]+:[a-z0-9-]+$",aid): raise SystemExit(f"adjacency_queue.jsonl:{n}: invalid adjacency_id {aid}")
    if aid in ids: raise SystemExit(f"adjacency_queue.jsonl:{n}: duplicate {aid}")
    ids.add(aid)
    if x.get("adjacency_type") not in allowed: raise SystemExit(f"adjacency_queue.jsonl:{n}: invalid type")
    if x.get("strategy_id") not in strats: raise SystemExit(f"adjacency_queue.jsonl:{n}: unknown strategy")
    if x.get("search_objective_id") not in objs: raise SystemExit(f"adjacency_queue.jsonl:{n}: unknown objective")
    if not isinstance(x.get("priority"),(int,float)) or not 0<=x["priority"]<=100: raise SystemExit(f"adjacency_queue.jsonl:{n}: bad priority")
    if not x.get("search_recipe") or not x.get("query_templates"): raise SystemExit(f"adjacency_queue.jsonl:{n}: missing recipe or queries")
for n,r in enumerate(runs,1):
    if (r.get("schema_version") or 0)<6: continue
    mode=r.get("adjacency_mode"); aids=r.get("adjacency_ids"); types=r.get("adjacency_types"); roots=r.get("adjacency_root_nodes")
    if mode not in {"generated","manual","none"}: raise SystemExit(f"search_runs.jsonl:{n}: invalid adjacency_mode")
    if not isinstance(aids,list) or not isinstance(types,list) or not isinstance(roots,list): raise SystemExit(f"search_runs.jsonl:{n}: adjacency fields must be lists")
    if mode=="generated" and not aids: raise SystemExit(f"search_runs.jsonl:{n}: generated adjacency requires IDs")
    if mode=="none" and (aids or types or roots): raise SystemExit(f"search_runs.jsonl:{n}: none mode requires empty adjacency fields")
    for aid in aids:
        if aid not in ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown adjacency_id {aid}")
    for typ in types:
        if typ not in allowed: raise SystemExit(f"search_runs.jsonl:{n}: unknown adjacency_type {typ}")
print(f"OK adjacency_hypotheses={len(rows)} v6_runs={sum(1 for r in runs if (r.get('schema_version') or 0)>=6)}")
