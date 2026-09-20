#!/usr/bin/env python3
import hashlib
from collections import Counter, defaultdict
from ti_common import INTEL, load_jsonl, write_jsonl

caps = load_jsonl("capabilities.jsonl")
runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
curated = load_jsonl("edges.jsonl")

def edge_id(a, t, b):
    return "EDGE:" + hashlib.sha1((a + "|" + t + "|" + b).encode()).hexdigest()[:12]

derived = []
seen = set()

def add(a, t, b, evidence):
    key = (a, t, b)
    if key in seen:
        return
    seen.add(key)
    derived.append({
        "edge_id": edge_id(a, t, b),
        "from": a,
        "type": t,
        "to": b,
        "confidence": "high",
        "evidence_ref": evidence,
        "provenance": "derived_structured_event"
    })

for r in runs:
    rid = r["search_run_id"]
    sid = r.get("strategy_id")
    if sid:
        add(sid, "PRODUCED", rid, "intelligence/search_runs.jsonl")
    for cid in r.get("new_capability_ids", []):
        add(rid, "PRODUCED", cid, "intelligence/search_runs.jsonl")
    for cid in r.get("strengthened_capability_ids", []):
        add(rid, "STRENGTHENS", cid, "intelligence/search_runs.jsonl")
    for exp in r.get("experiment_ids", []):
        add(rid, "CONTRIBUTED_TO", exp, "intelligence/search_runs.jsonl")
    for disposition in r.get("candidate_dispositions", []) or []:
        repository = disposition.get("repository")
        if repository:
            node = "REPO:" + repository + ("@" + disposition["revision"] if disposition.get("revision") else "")
            add(rid, "DISCOVERED", node, "intelligence/search_runs.jsonl")

for o in outs:
    oid = o["outcome_id"]
    for rid in o.get("origin_search_ids", []):
        add(rid, "PRODUCED", oid, "intelligence/outcomes.jsonl")
    for cid in o.get("contributing_capability_ids", []):
        add(cid, "CONTRIBUTED_TO", oid, "intelligence/outcomes.jsonl")
    if o.get("experiment_id"):
        add(oid, "VALIDATES", o["experiment_id"], "intelligence/outcomes.jsonl")

write_jsonl("derived_edges.jsonl", sorted(derived, key=lambda x: x["edge_id"]))

attention = Counter()
experiments = defaultdict(set)
for r in runs:
    for cid in r.get("new_capability_ids", []) + r.get("strengthened_capability_ids", []):
        attention[cid] += 1
        for exp in r.get("experiment_ids", []):
            experiments[cid].add(exp)

support = {}
for c in caps:
    components = len(c.get("primary_components") or [])
    targets = len(c.get("reusable_targets") or [])
    score = 0
    if c.get("evidence_state") == "watch":
        score += 3
    elif c.get("evidence_state") == "source_or_test_validated":
        score += 2
    elif c.get("evidence_state") == "benchmarked":
        score += 1
    if c.get("missing_piece"):
        score += 2
    if components < 2:
        score += 2
    if attention[c["capability_id"]] == 0:
        score += 1
    support[c["capability_id"]] = {
        "components": components,
        "targets": targets,
        "attention": attention[c["capability_id"]],
        "experiments": len(experiments[c["capability_id"]]),
        "gap_score": score
    }

priority = sorted(caps, key=lambda c: (-support[c["capability_id"]]["gap_score"], c["capability_id"]))[:12]
lines = [
    "# GRAPH HEALTH REPORT", "",
    f"- Curated edges: **{len(curated)}**",
    f"- Derived attribution edges: **{len(derived)}**",
    f"- Capability nodes: **{len(caps)}**",
    f"- Capabilities touched by measured search runs: **{sum(1 for c in caps if attention[c['capability_id']] > 0)}**", "",
    "## Highest-priority capability gaps", "",
    "| Capability | Evidence | Components | Run attention | Experiments | Gap score | Missing piece |",
    "|---|---|---:|---:|---:|---:|---|"
]
for c in priority:
    s = support[c["capability_id"]]
    lines.append(f"| {c['capability_id']} — {c['name']} | {c.get('evidence_state')} | {s['components']} | {s['attention']} | {s['experiments']} | {s['gap_score']} | {c.get('missing_piece') or '—'} |")
lines += [
    "", "## Graph policy", "",
    "- High gap score means **information value**, not commercial priority.",
    "- Prefer searches that close a named missing edge in an active experiment over searches that add another similar implementation.",
    "- A capability with many repositories but no experiment or outcome edge is a research cluster, not yet a validated asset.",
    "- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.", ""
]
(INTEL / "GRAPH_HEALTH.md").write_text("\n".join(lines), encoding="utf-8")
print(f"derived_edges={len(derived)}")
