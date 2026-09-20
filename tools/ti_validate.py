#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INTEL=ROOT/"intelligence"

def load_jsonl(name):
    path=INTEL/name
    out=[]
    if not path.exists():
        raise SystemExit(f"missing {path}")
    for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: obj=json.loads(line)
        except Exception as e: raise SystemExit(f"{name}:{n}: invalid JSON: {e}")
        out.append((n,obj))
    return out

caps=load_jsonl("capabilities.jsonl")
strats=load_jsonl("search_strategies.jsonl")
runs=load_jsonl("search_runs.jsonl")
outs=load_jsonl("outcomes.jsonl")
edges=load_jsonl("edges.jsonl")

def unique(rows,key,name):
    seen={}
    for n,o in rows:
        v=o.get(key)
        if not v: raise SystemExit(f"{name}:{n}: missing {key}")
        if v in seen: raise SystemExit(f"{name}:{n}: duplicate {key}={v} (first line {seen[v]})")
        seen[v]=n
    return set(seen)

cap_ids=unique(caps,"capability_id","capabilities.jsonl")
strat_ids=unique(strats,"strategy_id","search_strategies.jsonl")
run_ids=unique(runs,"search_run_id","search_runs.jsonl")
out_ids=unique(outs,"outcome_id","outcomes.jsonl")
edge_ids=unique(edges,"edge_id","edges.jsonl")

for n,o in caps:
    if not re.match(r"^CAP-\d{3,}$",o["capability_id"]): raise SystemExit(f"capabilities.jsonl:{n}: bad capability id")
    if o.get("confidence") not in {"low","medium","high"}: raise SystemExit(f"capabilities.jsonl:{n}: bad confidence")

for n,o in runs:
    if o.get("strategy_id") not in strat_ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown strategy_id {o.get('strategy_id')}")
    nums=[("candidate_count",o.get("candidate_count")),("deep_inspected",o.get("deep_inspected")),("retained_count",o.get("retained_count")),("master_promoted_count",o.get("master_promoted_count"))]
    for k,v in nums:
        if v is not None and (not isinstance(v,int) or v<0): raise SystemExit(f"search_runs.jsonl:{n}: {k} must be null or nonnegative integer")
    c,d,r,m=o.get("candidate_count"),o.get("deep_inspected"),o.get("retained_count"),o.get("master_promoted_count")
    if c is not None and d is not None and d>c: raise SystemExit(f"search_runs.jsonl:{n}: deep_inspected > candidate_count")
    if d is not None and r is not None and r>d: raise SystemExit(f"search_runs.jsonl:{n}: retained_count > deep_inspected")
    if r is not None and m is not None and m>r: raise SystemExit(f"search_runs.jsonl:{n}: master_promoted_count > retained_count")
    for cid in o.get("new_capability_ids",[])+o.get("strengthened_capability_ids",[]):
        if cid not in cap_ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown capability {cid}")

for n,o in outs:
    for rid in o.get("origin_search_ids",[]):
        if rid not in run_ids: raise SystemExit(f"outcomes.jsonl:{n}: unknown origin_search_id {rid}")
    for cid in o.get("contributing_capability_ids",[]):
        if cid not in cap_ids: raise SystemExit(f"outcomes.jsonl:{n}: unknown capability {cid}")
    lo,hi=o.get("engineering_days_saved_low"),o.get("engineering_days_saved_high")
    if lo is not None and hi is not None and lo>hi: raise SystemExit(f"outcomes.jsonl:{n}: engineering_days_saved_low > high")

known_prefixes=("REPO:","SOURCE:","TARGET:","EXP-","OPP:","TECH:","DATA:")
known_nodes=cap_ids|strat_ids|run_ids|out_ids
for n,o in edges:
    for side in ("from","to"):
        v=o.get(side)
        if not v: raise SystemExit(f"edges.jsonl:{n}: missing {side}")
        if v.startswith(("CAP-","STRAT:","RUN:","OUT:")) and v not in known_nodes:
            raise SystemExit(f"edges.jsonl:{n}: dangling {side} reference {v}")

print(f"OK capabilities={len(caps)} strategies={len(strats)} runs={len(runs)} outcomes={len(outs)} edges={len(edges)}")
