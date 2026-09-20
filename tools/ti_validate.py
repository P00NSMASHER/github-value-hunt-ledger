#!/usr/bin/env python3
import json, re
from ti_common import INTEL, load_jsonl, outcome_search_weights

def unique(rows, key, name):
    seen = {}
    for n, obj in enumerate(rows, 1):
        value = obj.get(key)
        if not value:
            raise SystemExit(f"{name}:{n}: missing {key}")
        if value in seen:
            raise SystemExit(f"{name}:{n}: duplicate {key}={value}; first line {seen[value]}")
        seen[value] = n
    return set(seen)

caps = load_jsonl("capabilities.jsonl")
strats = load_jsonl("search_strategies.jsonl")
runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
queries = load_jsonl("query_families.jsonl")
experiments = load_jsonl("experiment_registry.jsonl")
curated_edges = load_jsonl("edges.jsonl")
derived_edges = load_jsonl("derived_edges.jsonl") if (INTEL / "derived_edges.jsonl").exists() else []

cap_ids = unique(caps, "capability_id", "capabilities.jsonl")
strat_ids = unique(strats, "strategy_id", "search_strategies.jsonl")
run_ids = unique(runs, "search_run_id", "search_runs.jsonl")
out_ids = unique(outs, "outcome_id", "outcomes.jsonl")
query_ids = unique(queries, "query_family_id", "query_families.jsonl")
experiment_ids = unique(experiments, "experiment_id", "experiment_registry.jsonl")
unique(curated_edges, "edge_id", "edges.jsonl")
unique(derived_edges, "edge_id", "derived_edges.jsonl")

for n, c in enumerate(caps, 1):
    if not re.match(r"^CAP-\d{3,}$", c["capability_id"]):
        raise SystemExit(f"capabilities.jsonl:{n}: bad capability id")
    if c.get("confidence") not in {"low", "medium", "high"}:
        raise SystemExit(f"capabilities.jsonl:{n}: bad confidence")

for n, s in enumerate(strats, 1):
    parent = s.get("parent_strategy_id")
    if parent and parent not in strat_ids:
        raise SystemExit(f"search_strategies.jsonl:{n}: missing parent strategy {parent}")

for n, r in enumerate(runs, 1):
    sid = r.get("strategy_id")
    if sid not in strat_ids:
        raise SystemExit(f"search_runs.jsonl:{n}: unknown strategy_id {sid}")

    qid = r.get("query_family_id")
    if qid:
        if not re.match(r"^QF:[a-z0-9-]+$", qid):
            raise SystemExit(f"search_runs.jsonl:{n}: malformed query_family_id {qid}")
        if qid not in query_ids:
            raise SystemExit(f"search_runs.jsonl:{n}: unknown query_family_id {qid}")

    for key in ["candidate_count", "deep_inspected", "retained_count", "master_promoted_count"]:
        value = r.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise SystemExit(f"search_runs.jsonl:{n}: {key} must be null or nonnegative integer")

    c, d, k, m = r.get("candidate_count"), r.get("deep_inspected"), r.get("retained_count"), r.get("master_promoted_count")
    if c is not None and d is not None and d > c:
        raise SystemExit(f"search_runs.jsonl:{n}: deep_inspected > candidate_count")
    if d is not None and k is not None and k > d:
        raise SystemExit(f"search_runs.jsonl:{n}: retained_count > deep_inspected")
    if k is not None and m is not None and m > k:
        raise SystemExit(f"search_runs.jsonl:{n}: master_promoted_count > retained_count")

    for cid in r.get("new_capability_ids", []) + r.get("strengthened_capability_ids", []):
        if cid not in cap_ids:
            raise SystemExit(f"search_runs.jsonl:{n}: unknown capability {cid}")
    for exp in r.get("experiment_ids", []):
        if exp not in experiment_ids:
            raise SystemExit(f"search_runs.jsonl:{n}: unknown experiment {exp}")

    seen_disp = set()
    for disp in r.get("candidate_dispositions", []) or []:
        key = (disp.get("repository"), disp.get("revision"))
        if key in seen_disp and key != (None, None):
            raise SystemExit(f"search_runs.jsonl:{n}: duplicate candidate disposition {key}")
        seen_disp.add(key)

for n, o in enumerate(outs, 1):
    origins = list(dict.fromkeys(o.get("origin_search_ids", [])))
    for rid in origins:
        if rid not in run_ids:
            raise SystemExit(f"outcomes.jsonl:{n}: unknown origin_search_id {rid}")

    explicit = o.get("search_credit_weights")
    if explicit is not None:
        if not isinstance(explicit, dict):
            raise SystemExit(f"outcomes.jsonl:{n}: search_credit_weights must be an object")
        if set(explicit) != set(origins):
            raise SystemExit(f"outcomes.jsonl:{n}: explicit credit keys must exactly match origin_search_ids")
        for rid, value in explicit.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise SystemExit(f"outcomes.jsonl:{n}: invalid credit weight for {rid}")
        total = sum(explicit.values())
        if origins and abs(total - 1.0) > 1e-6:
            raise SystemExit(f"outcomes.jsonl:{n}: search_credit_weights sum to {total}, expected 1")

    normalized = outcome_search_weights(o)
    if origins and abs(sum(normalized.values()) - 1.0) > 1e-9:
        raise SystemExit(f"outcomes.jsonl:{n}: normalized outcome credit does not sum to 1")
    if not origins and normalized:
        raise SystemExit(f"outcomes.jsonl:{n}: outcome credit exists without origin searches")

    for cid in o.get("contributing_capability_ids", []):
        if cid not in cap_ids:
            raise SystemExit(f"outcomes.jsonl:{n}: unknown capability {cid}")
    exp = o.get("experiment_id")
    if exp and exp not in experiment_ids:
        raise SystemExit(f"outcomes.jsonl:{n}: unknown experiment_id {exp}")

    low, high = o.get("engineering_days_saved_low"), o.get("engineering_days_saved_high")
    if low is not None and high is not None and low > high:
        raise SystemExit(f"outcomes.jsonl:{n}: engineering_days_saved_low > high")

known = cap_ids | strat_ids | run_ids | out_ids | query_ids | experiment_ids
for name, edges in [("edges.jsonl", curated_edges), ("derived_edges.jsonl", derived_edges)]:
    for n, e in enumerate(edges, 1):
        for side in ("from", "to"):
            value = e.get(side)
            if not value:
                raise SystemExit(f"{name}:{n}: missing {side}")
            if value.startswith(("CAP-", "STRAT:", "RUN:", "OUT:", "QF:", "EXP-")) and value not in known:
                raise SystemExit(f"{name}:{n}: dangling {side} reference {value}")
        if "credit_weight" in e:
            value = e["credit_weight"]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise SystemExit(f"{name}:{n}: invalid credit_weight {value}")

policy_path = INTEL / "search_policy.json"
if policy_path.exists():
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    allocations = policy.get("strategy_allocation", [])
    if allocations:
        total = sum(x.get("allocation", 0) for x in allocations)
        if not 0.999 <= total <= 1.001:
            raise SystemExit(f"search_policy.json: allocations sum to {total}, expected 1")

print(
    f"OK capabilities={len(caps)} strategies={len(strats)} runs={len(runs)} "
    f"outcomes={len(outs)} queries={len(queries)} experiments={len(experiments)} "
    f"curated_edges={len(curated_edges)} derived_edges={len(derived_edges)}"
)
